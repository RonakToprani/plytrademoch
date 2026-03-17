"""
copy_trading/detector.py — Snapshot-diffing trade detection engine.

Responsibilities:
  • detect_changes(address)        — compare latest vs previous snapshot, emit TradeSignals
  • _classify_change()             — NEW_OPEN, INCREASE, DECREASE, CLOSE, FLIP
  • _filter_signals()              — drop delta-neutral pairs and sub-$100 whale changes
  • run(signal_queue)              — async loop; triggers detection after each tracker poll

Detection logic (per token_id):
  ┌───────────────────────────────────────────────────────────────────┐
  │  Exists in new, not in old  →  OPEN   (whale opened new position) │
  │  new.size > old.size        →  INCREASE                           │
  │  new.size < old.size > 0    →  DECREASE                           │
  │  new.size == 0 / missing    →  CLOSE                              │
  │  side flipped               →  FLIP   (e.g. YES→NO on same mkt)   │
  └───────────────────────────────────────────────────────────────────┘

Filtering rules:
  1. Ignore if whale's USD value of the delta < MIN_WHALE_DELTA_USD ($100)
  2. Ignore delta-neutral pairs: if whale holds both YES and NO on the same
     market (same market_slug) after the change, skip both legs.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from config.settings import settings
from data.database import Database
from data.models import TradeSignal, WalletSnapshot
from utils.logger import get_logger

logger = get_logger(__name__)

# Minimum absolute whale position change (in USD) to trigger a signal
_MIN_WHALE_DELTA_USD = 100.0

# Actions
ACTION_OPEN = "OPEN"
ACTION_INCREASE = "INCREASE"
ACTION_DECREASE = "DECREASE"
ACTION_CLOSE = "CLOSE"
ACTION_FLIP = "FLIP"


class TradeDetector:
    """
    Compares consecutive wallet snapshots to detect whale trades.

    Usage:
        detector = TradeDetector(db)
        signals = await detector.detect_changes("0xABCD...")
        # --- or run as a continuous loop ---
        queue: asyncio.Queue[TradeSignal] = asyncio.Queue()
        await detector.run(queue)
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def detect_changes(self, address: str) -> list[TradeSignal]:
        """
        Compare the two most recent snapshots for *address* and return a
        list of TradeSignal objects describing position changes.

        Returns an empty list when:
          • fewer than two snapshots exist (nothing to diff)
          • the two snapshots share the same timestamp (no new poll yet)
          • all detected changes are filtered out
        """
        latest = await self._db.get_latest_snapshot(address)
        if not latest:
            return []

        latest_ts = latest[0].timestamp.isoformat()
        previous = await self._db.get_previous_snapshot(address, latest_ts)
        if not previous:
            # First snapshot ever — nothing to compare yet
            return []

        signals = self._diff_snapshots(address, previous, latest)
        filtered = self._filter_signals(signals)

        if filtered:
            logger.info(
                "trade_signals_detected",
                address=address[:10],
                count=len(filtered),
                actions=[s.action for s in filtered],
            )

        return filtered

    async def detect_all_active(self) -> list[TradeSignal]:
        """
        Run detection for every active wallet and return the merged signal list.
        """
        wallets = await self._db.get_active_wallets()
        all_signals: list[TradeSignal] = []
        for wallet in wallets:
            try:
                signals = await self.detect_changes(wallet.address)
                all_signals.extend(signals)
            except Exception as exc:
                logger.warning(
                    "detect_changes_error",
                    address=wallet.address[:10],
                    error=str(exc),
                )
        return all_signals

    async def run(self, signal_queue: asyncio.Queue[TradeSignal]) -> None:
        """
        Continuously poll for new snapshots and push detected TradeSignals
        onto *signal_queue* for downstream consumers (executor, risk manager).

        Polls every POLL_INTERVAL_SECONDS seconds.
        Runs until cancelled.
        """
        logger.info(
            "trade_detector_started",
            poll_interval=settings.poll_interval_seconds,
        )
        try:
            while True:
                signals = await self.detect_all_active()
                for signal in signals:
                    await signal_queue.put(signal)
                await asyncio.sleep(settings.poll_interval_seconds)
        except asyncio.CancelledError:
            logger.info("trade_detector_cancelled")
            raise

    # ------------------------------------------------------------------
    # Diff logic
    # ------------------------------------------------------------------

    def _diff_snapshots(
        self,
        address: str,
        old_snapshots: list[WalletSnapshot],
        new_snapshots: list[WalletSnapshot],
    ) -> list[TradeSignal]:
        """
        Diff two snapshot batches and return raw (unfiltered) TradeSignals.

        Keyed by token_id; detects OPEN, INCREASE, DECREASE, CLOSE, FLIP.
        """
        old_by_token: dict[str, WalletSnapshot] = {s.token_id: s for s in old_snapshots}
        new_by_token: dict[str, WalletSnapshot] = {s.token_id: s for s in new_snapshots}

        signals: list[TradeSignal] = []
        now = datetime.now(timezone.utc)

        # Tokens that appear in the new snapshot
        for token_id, new_snap in new_by_token.items():
            old_snap = old_by_token.get(token_id)

            if old_snap is None:
                # Completely new position
                signals.append(TradeSignal(
                    wallet=address,
                    token_id=token_id,
                    market_slug=new_snap.market_slug,
                    side=new_snap.side,
                    action=ACTION_OPEN,
                    whale_size_delta=new_snap.size,
                    current_price=new_snap.current_price,
                    detected_at=now,
                ))
                continue

            # Same token — check for side flip first
            if old_snap.side != new_snap.side:
                signals.append(TradeSignal(
                    wallet=address,
                    token_id=token_id,
                    market_slug=new_snap.market_slug,
                    side=new_snap.side,
                    action=ACTION_FLIP,
                    whale_size_delta=new_snap.size,
                    current_price=new_snap.current_price,
                    detected_at=now,
                ))
                continue

            size_delta = new_snap.size - old_snap.size
            if size_delta > 0:
                signals.append(TradeSignal(
                    wallet=address,
                    token_id=token_id,
                    market_slug=new_snap.market_slug,
                    side=new_snap.side,
                    action=ACTION_INCREASE,
                    whale_size_delta=size_delta,
                    current_price=new_snap.current_price,
                    detected_at=now,
                ))
            elif size_delta < 0:
                signals.append(TradeSignal(
                    wallet=address,
                    token_id=token_id,
                    market_slug=new_snap.market_slug,
                    side=new_snap.side,
                    action=ACTION_DECREASE,
                    whale_size_delta=abs(size_delta),
                    current_price=new_snap.current_price,
                    detected_at=now,
                ))
            # size_delta == 0: no change, emit nothing

        # Tokens that disappeared (closed positions)
        for token_id, old_snap in old_by_token.items():
            if token_id not in new_by_token:
                signals.append(TradeSignal(
                    wallet=address,
                    token_id=token_id,
                    market_slug=old_snap.market_slug,
                    side=old_snap.side,
                    action=ACTION_CLOSE,
                    whale_size_delta=old_snap.size,
                    current_price=old_snap.current_price,
                    detected_at=now,
                ))

        return signals

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _filter_signals(self, signals: list[TradeSignal]) -> list[TradeSignal]:
        """
        Apply two filters:

        1. **Minimum delta**: drop signals where the whale's USD value of the
           change is below _MIN_WHALE_DELTA_USD.
        2. **Delta-neutral**: if the whale now holds BOTH YES and NO on the
           same market_slug, drop signals for that market (hedged position,
           no directional conviction to copy).
        """
        # Filter 1: minimum delta
        meaningful: list[TradeSignal] = []
        for sig in signals:
            usd_delta = sig.whale_size_delta * max(sig.current_price, 0.01)
            if usd_delta >= _MIN_WHALE_DELTA_USD:
                meaningful.append(sig)
            else:
                logger.debug(
                    "signal_filtered_small_delta",
                    address=sig.wallet[:10],
                    token_id=sig.token_id[:10],
                    usd_delta=round(usd_delta, 2),
                )

        # Filter 2: delta-neutral — skip markets where both sides appear in the
        # OPEN/INCREASE/FLIP signals (whale is hedged, not directional)
        slugs_with_both_sides: set[str] = self._find_delta_neutral_slugs(meaningful)

        filtered: list[TradeSignal] = []
        for sig in meaningful:
            if sig.market_slug in slugs_with_both_sides:
                logger.debug(
                    "signal_filtered_delta_neutral",
                    address=sig.wallet[:10],
                    market_slug=sig.market_slug,
                )
            else:
                filtered.append(sig)

        return filtered

    @staticmethod
    def _find_delta_neutral_slugs(signals: list[TradeSignal]) -> set[str]:
        """
        Return the set of market_slugs that have both a YES and a NO entry
        signal among *signals* — indicating the whale is delta-neutral.

        Only checks OPEN, INCREASE, FLIP actions (entry signals).
        """
        entry_actions = {ACTION_OPEN, ACTION_INCREASE, ACTION_FLIP}
        sides_by_slug: dict[str, set[str]] = {}
        for sig in signals:
            if sig.action not in entry_actions:
                continue
            sides_by_slug.setdefault(sig.market_slug, set()).add(sig.side)

        return {slug for slug, sides in sides_by_slug.items() if len(sides) > 1}
