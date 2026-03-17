"""
copy_trading/scanner.py — Wallet discovery and scoring engine.

Responsibilities:
  • discover_wallets()  — paginate the Data API leaderboard to find top traders
  • score_wallet()      — fetch full trade history, compute a 0–100 composite score
  • filter_wallets()    — apply minimum P&L / win-rate / trade-count thresholds
  • estimate_bankroll() — approximate whale bankroll for proportional sizing
  • rescan_all()        — daily re-score all tracked wallets, deactivate underperformers

Scoring formula (weights sum to 1.0):
  score = 0.30 * norm_pnl
        + 0.25 * win_rate          (already 0–1)
        + 0.20 * norm_roi
        + 0.15 * consistency_score (Sharpe-like ratio of per-trade returns)
        + 0.10 * recency_score     (active in last 30 days → 1.0, else scaled)

Final score is multiplied by 100 and clamped to [0, 100].
"""

from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from config.settings import settings
from core.client import PolymarketClient
from data.database import Database
from data.models import TrackedWallet
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Leaderboard pagination: fetch up to this many pages of top traders
_LEADERBOARD_PAGE_SIZE = 100
_LEADERBOARD_MAX_PAGES = 5

# History pagination: fetch up to this many trades per wallet for scoring
_HISTORY_PAGE_SIZE = 500
_HISTORY_MAX_PAGES = 4

# Normalisation caps: PnL and ROI values above these are treated as 1.0
_PNL_CAP = 1_000_000.0   # $1M lifetime P&L → max normalised score
_ROI_CAP = 10.0          # 1000% ROI → max normalised score

# Recency window in days: active within this window scores 1.0
_RECENCY_WINDOW_DAYS = 30


# ---------------------------------------------------------------------------
# WalletScanner
# ---------------------------------------------------------------------------

class WalletScanner:
    """Discovers and scores top Polymarket traders."""

    def __init__(self, client: PolymarketClient, db: Database) -> None:
        self._client = client
        self._db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def discover_wallets(self) -> list[TrackedWallet]:
        """
        Fetch the Data API leaderboard, score qualifying wallets, persist them,
        and return the top-scoring results (up to MAX_TRACKED_WALLETS).
        """
        logger.info("discover_wallets_start")
        raw_entries = await self._fetch_leaderboard()
        logger.info("leaderboard_fetched", count=len(raw_entries))

        # Pre-filter: only score wallets that pass the basic thresholds so we
        # don't waste API calls on obviously ineligible traders.
        candidates = [e for e in raw_entries if self._passes_quick_filter(e)]
        logger.info("candidates_after_prefilter", count=len(candidates))

        wallets: list[TrackedWallet] = []
        for entry in candidates:
            address = entry.get("proxyWallet") or entry.get("address") or entry.get("wallet", "")
            if not address:
                continue
            try:
                wallet = await self.score_wallet(address, leaderboard_entry=entry)
                if wallet:
                    wallets.append(wallet)
            except Exception as exc:
                logger.warning("score_wallet_failed", address=address[:10], error=str(exc))

        # Sort by composite score, keep top N
        wallets.sort(key=lambda w: w.score, reverse=True)
        top_wallets = wallets[: settings.max_tracked_wallets]

        # Persist
        for wallet in top_wallets:
            await self._db.upsert_wallet(wallet)
            logger.info(
                "wallet_upserted",
                address=wallet.address[:10],
                score=round(wallet.score, 2),
                pnl=wallet.lifetime_pnl,
            )

        logger.info("discover_wallets_done", discovered=len(top_wallets))
        return top_wallets

    async def score_wallet(
        self,
        address: str,
        *,
        leaderboard_entry: dict[str, Any] | None = None,
    ) -> TrackedWallet | None:
        """
        Compute the composite score for a single wallet.

        Returns a TrackedWallet (not yet persisted) or None if the wallet
        fails hard thresholds after full analysis.
        """
        history = await self._fetch_full_history(address)
        if not history:
            logger.debug("score_wallet_no_history", address=address[:10])
            return None

        lifetime_pnl = self._calc_lifetime_pnl(history, leaderboard_entry)
        win_rate = self._calc_win_rate(history)
        roi = self._calc_roi(history, leaderboard_entry)
        total_trades = len(history)
        consistency = self._calc_consistency(history)
        recency = self._calc_recency(history)
        bankroll = await self.estimate_bankroll(address)

        # Apply hard thresholds
        if not self._passes_thresholds(lifetime_pnl, win_rate, total_trades):
            return None

        score = self._composite_score(lifetime_pnl, win_rate, roi, consistency, recency)

        alias = self._derive_alias(address, leaderboard_entry)

        return TrackedWallet(
            address=address,
            alias=alias,
            lifetime_pnl=lifetime_pnl,
            win_rate=win_rate,
            roi=roi,
            total_trades=total_trades,
            score=score,
            is_active=True,
            last_scanned=datetime.now(timezone.utc),
            estimated_bankroll=bankroll,
        )

    def filter_wallets(self, wallets: list[TrackedWallet]) -> list[TrackedWallet]:
        """Return only wallets that pass all configured minimum thresholds."""
        return [
            w for w in wallets
            if self._passes_thresholds(w.lifetime_pnl, w.win_rate, w.total_trades)
        ]

    async def estimate_bankroll(self, address: str) -> float:
        """
        Estimate a wallet's bankroll as the sum of current position values.

        If positions are unavailable, returns 0.0 — callers fall back to the
        5× largest-visible-position heuristic in ProportionalSizer.
        """
        try:
            positions = await self._client.get_user_positions(address)
            total = sum(
                float(p.get("size", 0)) * float(p.get("curPrice", p.get("currentPrice", 0)))
                for p in positions
            )
            return round(total, 2)
        except Exception as exc:
            logger.debug("estimate_bankroll_failed", address=address[:10], error=str(exc))
            return 0.0

    async def rescan_all(self) -> None:
        """
        Re-score every tracked wallet.  Deactivate any that no longer meet
        minimum thresholds or that can no longer be fetched.
        """
        wallets = await self._db.get_all_wallets()
        logger.info("rescan_all_start", count=len(wallets))
        for wallet in wallets:
            try:
                updated = await self.score_wallet(wallet.address)
                if updated is None:
                    logger.info(
                        "wallet_deactivated_below_threshold",
                        address=wallet.address[:10],
                    )
                    await self._db.deactivate_wallet(wallet.address)
                else:
                    updated.alias = wallet.alias or updated.alias
                    await self._db.upsert_wallet(updated)
                    logger.info(
                        "wallet_rescored",
                        address=wallet.address[:10],
                        score=round(updated.score, 2),
                    )
            except Exception as exc:
                logger.warning("rescan_wallet_failed", address=wallet.address[:10], error=str(exc))
        logger.info("rescan_all_done")

    # ------------------------------------------------------------------
    # Data fetching helpers
    # ------------------------------------------------------------------

    async def _fetch_leaderboard(self) -> list[dict[str, Any]]:
        """Paginate the leaderboard and return all entries."""
        entries: list[dict[str, Any]] = []
        for page in range(_LEADERBOARD_MAX_PAGES):
            offset = page * _LEADERBOARD_PAGE_SIZE
            try:
                page_data = await self._client.get_leaderboard(
                    limit=_LEADERBOARD_PAGE_SIZE,
                    offset=offset,
                )
            except Exception as exc:
                logger.warning("leaderboard_fetch_error", page=page, error=str(exc))
                break
            if not page_data:
                break
            entries.extend(page_data)
            if len(page_data) < _LEADERBOARD_PAGE_SIZE:
                break  # last page
        return entries

    async def _fetch_full_history(self, address: str) -> list[dict[str, Any]]:
        """Fetch up to _HISTORY_MAX_PAGES × _HISTORY_PAGE_SIZE trades for a wallet."""
        history: list[dict[str, Any]] = []
        for page in range(_HISTORY_MAX_PAGES):
            offset = page * _HISTORY_PAGE_SIZE
            try:
                page_data = await self._client.get_user_history(
                    address,
                    limit=_HISTORY_PAGE_SIZE,
                    offset=offset,
                )
            except Exception as exc:
                logger.debug("history_fetch_error", address=address[:10], page=page, error=str(exc))
                break
            if not page_data:
                break
            history.extend(page_data)
            if len(page_data) < _HISTORY_PAGE_SIZE:
                break
            # Small stagger to stay within rate limits when scoring many wallets
            await asyncio.sleep(0.5)
        return history

    # ------------------------------------------------------------------
    # Scoring components
    # ------------------------------------------------------------------

    def _calc_lifetime_pnl(
        self,
        history: list[dict[str, Any]],
        leaderboard_entry: dict[str, Any] | None,
    ) -> float:
        """
        Prefer the leaderboard's aggregated P&L (more accurate) over summing
        individual trade P&L fields, which may be incomplete.
        """
        if leaderboard_entry:
            for key in ("profitLoss", "pnl", "profit", "totalProfit"):
                val = leaderboard_entry.get(key)
                if val is not None:
                    return float(val)

        # Fall back: sum 'profit' or 'pnl' fields from history
        total = sum(
            float(t.get("profit", t.get("pnl", t.get("cashPnl", 0))))
            for t in history
        )
        return round(total, 2)

    def _calc_win_rate(self, history: list[dict[str, Any]]) -> float:
        """Fraction of trades with positive P&L (0–1)."""
        if not history:
            return 0.0
        wins = sum(
            1 for t in history
            if float(t.get("profit", t.get("pnl", t.get("cashPnl", 0)))) > 0
        )
        return wins / len(history)

    def _calc_roi(
        self,
        history: list[dict[str, Any]],
        leaderboard_entry: dict[str, Any] | None,
    ) -> float:
        """
        Return on investment as a decimal (1.0 = 100% return).

        Prefer leaderboard field if available.
        """
        if leaderboard_entry:
            for key in ("roi", "returnOnInvestment", "percentReturn"):
                val = leaderboard_entry.get(key)
                if val is not None:
                    raw = float(val)
                    # Normalise: some APIs return a percentage (e.g. 45.2), others a decimal
                    return raw / 100.0 if raw > 2.0 else raw

        # Fall back: total_pnl / total_invested
        total_pnl = self._calc_lifetime_pnl(history, None)
        total_invested = sum(
            float(t.get("investment", t.get("amount", t.get("size", 0))))
            * float(t.get("price", t.get("avgPrice", 1)))
            for t in history
        )
        if total_invested <= 0:
            return 0.0
        return round(total_pnl / total_invested, 4)

    def _calc_consistency(self, history: list[dict[str, Any]]) -> float:
        """
        Sharpe-like consistency score: mean(returns) / std(returns).

        Normalised to [0, 1] using a soft sigmoid on the raw Sharpe.
        """
        if len(history) < 5:
            return 0.0

        returns = [
            float(t.get("profit", t.get("pnl", t.get("cashPnl", 0))))
            for t in history
        ]
        n = len(returns)
        mean = sum(returns) / n
        variance = sum((r - mean) ** 2 for r in returns) / n
        std = math.sqrt(variance)
        if std == 0:
            return 1.0 if mean > 0 else 0.0

        sharpe = mean / std
        # Sigmoid centred at 0, saturates at high positive Sharpe values
        score = 1.0 / (1.0 + math.exp(-sharpe))
        return round(score, 4)

    def _calc_recency(self, history: list[dict[str, Any]]) -> float:
        """
        Score based on how recently the wallet was active.

        1.0  → last trade within 30 days
        0.0  → no trade in 180 days or more
        Linear decay between 30 and 180 days.
        """
        cutoff_full = datetime.now(timezone.utc) - timedelta(days=_RECENCY_WINDOW_DAYS)
        cutoff_zero = datetime.now(timezone.utc) - timedelta(days=180)

        last_trade_dt: datetime | None = None
        for trade in history:
            raw_ts = trade.get("timestamp", trade.get("createdAt", trade.get("date")))
            if raw_ts is None:
                continue
            try:
                if isinstance(raw_ts, (int, float)):
                    dt = datetime.fromtimestamp(raw_ts, tz=timezone.utc)
                else:
                    dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if last_trade_dt is None or dt > last_trade_dt:
                    last_trade_dt = dt
            except (ValueError, OSError):
                continue

        if last_trade_dt is None:
            return 0.0
        if last_trade_dt >= cutoff_full:
            return 1.0
        if last_trade_dt <= cutoff_zero:
            return 0.0
        # Linear decay
        total_range = (cutoff_full - cutoff_zero).total_seconds()
        elapsed = (last_trade_dt - cutoff_zero).total_seconds()
        return round(elapsed / total_range, 4)

    def _composite_score(
        self,
        lifetime_pnl: float,
        win_rate: float,
        roi: float,
        consistency: float,
        recency: float,
    ) -> float:
        """
        Weighted composite score, scaled to 0–100.

        score = (0.30 * norm_pnl) + (0.25 * win_rate) + (0.20 * norm_roi)
              + (0.15 * consistency) + (0.10 * recency)
        """
        norm_pnl = min(max(lifetime_pnl, 0.0) / _PNL_CAP, 1.0)
        norm_roi = min(max(roi, 0.0) / _ROI_CAP, 1.0)
        win_rate_clamped = max(0.0, min(win_rate, 1.0))

        raw = (
            0.30 * norm_pnl
            + 0.25 * win_rate_clamped
            + 0.20 * norm_roi
            + 0.15 * consistency
            + 0.10 * recency
        )
        return round(min(max(raw * 100.0, 0.0), 100.0), 2)

    # ------------------------------------------------------------------
    # Filtering helpers
    # ------------------------------------------------------------------

    def _passes_quick_filter(self, entry: dict[str, Any]) -> bool:
        """
        Lightweight pre-filter on leaderboard data before making extra API calls.
        Checks P&L and trade count only (win rate may not be on the leaderboard row).
        """
        pnl_keys = ("profitLoss", "pnl", "profit", "totalProfit")
        pnl = next(
            (float(entry[k]) for k in pnl_keys if entry.get(k) is not None),
            None,
        )
        if pnl is None or pnl < settings.min_whale_pnl:
            return False

        trade_keys = ("numTrades", "trades", "totalTrades", "tradeCount")
        trades = next(
            (int(entry[k]) for k in trade_keys if entry.get(k) is not None),
            None,
        )
        if trades is not None and trades < settings.min_trades:
            return False

        return True

    def _passes_thresholds(
        self,
        lifetime_pnl: float,
        win_rate: float,
        total_trades: int,
    ) -> bool:
        """Hard thresholds from settings."""
        return (
            lifetime_pnl >= settings.min_whale_pnl
            and win_rate >= settings.min_win_rate
            and total_trades >= settings.min_trades
        )

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_alias(
        address: str,
        leaderboard_entry: dict[str, Any] | None,
    ) -> str:
        """Return a human-readable alias from the leaderboard entry or a truncated address."""
        if leaderboard_entry:
            for key in ("name", "username", "displayName", "alias"):
                val = leaderboard_entry.get(key)
                if val and isinstance(val, str) and val.strip():
                    return val.strip()
        # Fallback: "0xABCD…EF12"
        return f"{address[:6]}…{address[-4:]}" if len(address) > 10 else address
