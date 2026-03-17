"""
copy_trading/tracker.py — Real-time position monitoring for tracked whale wallets.

Responsibilities:
  • poll_positions(address)  — fetch current positions from the Data API
  • take_snapshot(address)   — convert raw positions into WalletSnapshot rows & persist
  • run()                    — async poll loop: iterate all active wallets every
                               POLL_INTERVAL_SECONDS, staggered to stay inside the
                               60 req/min rate limit

Stagger logic:
  With up to MAX_TRACKED_WALLETS=10 wallets and a 30-second poll interval, we have
  3 seconds between each wallet's fetch.  That's comfortably within the 60 req/min
  budget (each wallet poll = 1 request).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from config.settings import settings
from core.client import PolymarketClient
from data.database import Database
from data.models import WalletSnapshot
from utils.logger import get_logger

logger = get_logger(__name__)

# Minimum USD value of a position to be recorded (avoids dust positions)
_MIN_POSITION_VALUE = 0.01


class WalletTracker:
    """
    Polls active whale wallets for position changes and persists snapshots.

    Usage:
        tracker = WalletTracker(client, db)
        await tracker.run()          # runs forever; cancel to stop
    """

    def __init__(self, client: PolymarketClient, db: Database) -> None:
        self._client = client
        self._db = db
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def poll_positions(self, address: str) -> list[dict[str, Any]]:
        """
        Fetch current open positions for *address* from the Data API.

        Returns the raw list of position dicts; an empty list on error.
        """
        try:
            positions = await self._client.get_user_positions(address)
            logger.debug(
                "positions_fetched",
                address=address[:10],
                count=len(positions),
            )
            return positions
        except Exception as exc:
            logger.warning(
                "poll_positions_failed",
                address=address[:10],
                error=str(exc),
            )
            return []

    async def take_snapshot(self, address: str) -> list[WalletSnapshot]:
        """
        Poll positions for *address*, convert to WalletSnapshot objects,
        save them to the database, and return the snapshot list.

        Returns an empty list if the wallet has no open positions or the
        fetch fails.
        """
        raw_positions = await self.poll_positions(address)
        if not raw_positions:
            return []

        now = datetime.now(timezone.utc)
        snapshots: list[WalletSnapshot] = []

        for pos in raw_positions:
            snapshot = self._position_to_snapshot(pos, address, now)
            if snapshot is not None:
                snapshots.append(snapshot)

        if snapshots:
            await self._db.save_snapshots(snapshots)
            logger.info(
                "snapshot_saved",
                address=address[:10],
                positions=len(snapshots),
                timestamp=now.isoformat(),
            )

        return snapshots

    async def run(self) -> None:
        """
        Continuously poll all active tracked wallets in a round-robin loop.

        Each wallet is polled in turn; requests are staggered evenly across
        the poll interval so we never burst the API rate limit.

        Runs until cancelled (e.g. via asyncio.CancelledError).
        """
        self._running = True
        logger.info(
            "wallet_tracker_started",
            poll_interval=settings.poll_interval_seconds,
        )
        try:
            while self._running:
                wallets = await self._db.get_active_wallets()
                if not wallets:
                    logger.debug("no_active_wallets_sleeping")
                    await asyncio.sleep(settings.poll_interval_seconds)
                    continue

                # Spread requests evenly across the poll interval
                stagger = settings.poll_interval_seconds / len(wallets)

                for wallet in wallets:
                    if not self._running:
                        break
                    try:
                        await self.take_snapshot(wallet.address)
                    except Exception as exc:
                        logger.warning(
                            "snapshot_error",
                            address=wallet.address[:10],
                            error=str(exc),
                        )
                    await asyncio.sleep(stagger)

        except asyncio.CancelledError:
            logger.info("wallet_tracker_cancelled")
            self._running = False
            raise

    def stop(self) -> None:
        """Signal the run loop to exit after its current iteration."""
        self._running = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _position_to_snapshot(
        pos: dict[str, Any],
        wallet_address: str,
        timestamp: datetime,
    ) -> WalletSnapshot | None:
        """
        Convert a raw Data API position dict into a WalletSnapshot.

        Handles multiple field naming conventions observed in the API:
          • token_id  : "asset" | "tokenId" | "token_id" | "conditionId"
          • side      : "outcome" | "side" | defaults to "YES" for token index 0
          • size      : "size" | "amount" | "shares"
          • price     : "curPrice" | "currentPrice" | "price" | "avgPrice"
          • entry     : "avgPrice" | "averagePrice" | "entryPrice" | "price"
          • slug      : "market" | "slug" | "marketSlug" | "conditionId"

        Returns None for dust positions (value below _MIN_POSITION_VALUE).
        """
        token_id: str = (
            pos.get("asset")
            or pos.get("tokenId")
            or pos.get("token_id")
            or pos.get("conditionId")
            or ""
        )
        if not token_id:
            return None

        # Determine YES/NO side
        raw_side: str = (
            pos.get("outcome")
            or pos.get("side")
            or ""
        )
        if raw_side.upper() in ("YES", "NO"):
            side = raw_side.upper()
        else:
            # Polymarket Data API: outcomeIndex 0 → YES, 1 → NO
            idx = pos.get("outcomeIndex", pos.get("outcome_index", 0))
            side = "YES" if int(idx) == 0 else "NO"

        size = float(pos.get("size", pos.get("amount", pos.get("shares", 0))))

        current_price = float(
            pos.get("curPrice", pos.get("currentPrice", pos.get("price", 0)))
        )

        # Skip dust
        if size * max(current_price, 0.01) < _MIN_POSITION_VALUE:
            return None

        avg_entry_price = float(
            pos.get("avgPrice", pos.get("averagePrice", pos.get("entryPrice", pos.get("price", 0))))
        )

        market_slug: str = (
            pos.get("market")
            or pos.get("slug")
            or pos.get("marketSlug")
            or pos.get("conditionId")
            or token_id
        )

        return WalletSnapshot(
            wallet_address=wallet_address,
            token_id=token_id,
            market_slug=market_slug,
            side=side,
            size=size,
            avg_entry_price=avg_entry_price,
            current_price=current_price,
            timestamp=timestamp,
        )
