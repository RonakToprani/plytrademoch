"""
risk/portfolio.py — Position tracking, mark-to-market P&L, and exposure calc.

Responsibilities:
  • mark_to_market()    — refresh current_price for all open positions via CLOB
  • total_exposure()    — sum of (size × current_price) across open trades
  • daily_pnl()         — realized + unrealized P&L since midnight UTC
  • generate_report()   — summary dict for dashboard and Telegram

All state is read from the SQLite database; this class holds no persistent
in-memory position cache (so the dashboard thread gets consistent reads).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from data.database import Database
from data.models import CopyTrade, DailyPnL
from utils.logger import get_logger

if TYPE_CHECKING:
    from core.client import PolymarketClient

logger = get_logger(__name__)


class Portfolio:
    """
    Reads open positions from the database, marks them to market, and
    computes aggregate P&L / exposure figures.

    Usage::

        portfolio = Portfolio(db, client)
        await portfolio.mark_to_market()
        exposure = await portfolio.total_exposure()
        report   = await portfolio.generate_report()
    """

    def __init__(self, db: Database, client: "PolymarketClient") -> None:
        self._db = db
        self._client = client

    # ------------------------------------------------------------------
    # Mark-to-market
    # ------------------------------------------------------------------

    async def mark_to_market(self) -> list[CopyTrade]:
        """
        Fetch the current mid price for every open position and update the
        database record.

        Returns the updated list of open trades.
        """
        open_trades = await self._db.get_open_trades()
        if not open_trades:
            return []

        updated: list[CopyTrade] = []
        for trade in open_trades:
            try:
                mid = await self._get_mid_price(trade.token_id)
                if mid is None:
                    continue

                unrealized_pnl = _unrealized_pnl(
                    trade.side, trade.size, trade.entry_price, mid
                )
                await self._db.update_trade(
                    trade.id,
                    current_price=mid,
                    pnl=unrealized_pnl,
                )
                # Reflect update locally for the return value
                trade.current_price = mid
                trade.pnl = unrealized_pnl
                updated.append(trade)

            except Exception as exc:
                logger.warning(
                    "mark_to_market_error",
                    trade_id=trade.id,
                    market_slug=trade.market_slug,
                    error=str(exc),
                )

        logger.info("mark_to_market_done", updated=len(updated), total=len(open_trades))
        return updated

    # ------------------------------------------------------------------
    # Exposure & P&L
    # ------------------------------------------------------------------

    async def total_exposure(self) -> float:
        """
        Return total portfolio exposure in USD: sum of (size × current_price)
        across all open (FILLED / PARTIAL) trades.
        """
        open_trades = await self._db.get_open_trades()
        exposure = sum(t.size * t.current_price for t in open_trades)
        return round(exposure, 2)

    async def daily_pnl(self) -> float:
        """
        Return today's total P&L (realized closed trades + unrealized open
        positions) since midnight UTC.
        """
        today = datetime.now(timezone.utc).date().isoformat()
        record = await self._db.get_daily_pnl(today)
        if record:
            return record.total_pnl

        # Fall back to computing on-the-fly from raw trade data
        summary = await self._db.get_portfolio_summary()
        return summary.get("today_pnl", 0.0)

    async def unrealized_pnl(self) -> float:
        """Sum of unrealized P&L across all open positions."""
        open_trades = await self._db.get_open_trades()
        return round(sum(t.pnl for t in open_trades), 4)

    async def realized_pnl(self) -> float:
        """Sum of P&L across all closed trades."""
        all_trades = await self._db.get_all_trades(limit=10_000, status="CLOSED")
        return round(sum(t.pnl for t in all_trades), 4)

    # ------------------------------------------------------------------
    # Daily snapshot
    # ------------------------------------------------------------------

    async def snapshot_daily_pnl(self) -> DailyPnL:
        """
        Compute and persist a DailyPnL record for today (upsert).

        Call this once per day at midnight UTC (or any time for a live
        intra-day snapshot).
        """
        today = datetime.now(timezone.utc).date().isoformat()

        closed_today = await self._db.get_all_trades(limit=10_000, status="CLOSED")
        # Filter to trades closed today
        closed_today = [
            t for t in closed_today
            if t.filled_at and t.filled_at.date().isoformat() == today
        ]

        realized = round(sum(t.pnl for t in closed_today), 4)
        unrealized = await self.unrealized_pnl()
        total = round(realized + unrealized, 4)
        num_trades = len(closed_today)
        wins = sum(1 for t in closed_today if t.pnl > 0)
        win_rate = (wins / num_trades) if num_trades > 0 else 0.0
        exposure = await self.total_exposure()

        record = DailyPnL(
            date=today,
            realized_pnl=realized,
            unrealized_pnl=unrealized,
            total_pnl=total,
            num_trades=num_trades,
            win_rate=win_rate,
            total_exposure=exposure,
        )
        await self._db.upsert_daily_pnl(record)
        logger.info(
            "daily_pnl_snapshot",
            date=today,
            realized=realized,
            unrealized=unrealized,
            total=total,
            num_trades=num_trades,
        )
        return record

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    async def generate_report(self) -> dict[str, Any]:
        """
        Build a summary dict suitable for the dashboard and Telegram alerts.

        Keys:
            total_pnl, today_pnl, unrealized_pnl, realized_pnl,
            total_exposure, open_trades, closed_trades, win_rate
        """
        summary = await self._db.get_portfolio_summary()
        unrealized = await self.unrealized_pnl()
        exposure = await self.total_exposure()

        report = {
            "total_pnl": round(summary.get("total_pnl", 0.0) + unrealized, 4),
            "today_pnl": summary.get("today_pnl", 0.0),
            "unrealized_pnl": unrealized,
            "realized_pnl": summary.get("total_pnl", 0.0),
            "total_exposure": exposure,
            "open_trades": summary.get("open_trades", 0),
            "closed_trades": summary.get("closed_trades", 0),
            "win_rate": round(summary.get("win_rate", 0.0), 4),
        }
        logger.debug("portfolio_report_generated", **report)
        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_mid_price(self, token_id: str) -> float | None:
        """
        Fetch the current mid price from the CLOB order book.

        Returns the mid = (best_bid + best_ask) / 2, or None on error.
        """
        try:
            book = await self._client.get_order_book(token_id)
            bids: list[dict] = book.get("bids", [])
            asks: list[dict] = book.get("asks", [])

            best_bid = float(bids[0]["price"]) if bids else None
            best_ask = float(asks[0]["price"]) if asks else None

            if best_bid is not None and best_ask is not None:
                return round((best_bid + best_ask) / 2, 4)
            if best_bid is not None:
                return best_bid
            if best_ask is not None:
                return best_ask
            return None

        except Exception as exc:
            logger.warning(
                "get_mid_price_error",
                token_id=token_id[:12],
                error=str(exc),
            )
            return None


# ------------------------------------------------------------------
# Module helpers
# ------------------------------------------------------------------

def _unrealized_pnl(side: str, size: float, entry: float, current: float) -> float:
    """Unrealized P&L for a long (BUY/YES/NO) position."""
    if side.upper() in ("YES", "NO", "BUY"):
        return round(size * (current - entry), 4)
    return round(size * (entry - current), 4)
