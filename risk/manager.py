"""
risk/manager.py — Pre-trade validation, stop-loss enforcement, and emergency shutdown.

Responsibilities:
  • check_order(signal, size)  — pre-trade guard: position limit, exposure, daily loss,
                                  VPN status, data freshness
  • check_stop_losses()        — close any open trade that has lost >50% of entry value
  • emergency_shutdown()       — cancel all open orders, send Telegram alert
  • run()                      — async loop: check_stop_losses + exposure every 30s

Guard rules (all must pass for check_order to return True):
  1. Position per market ≤ MAX_POSITION_PER_MARKET  ($20)
  2. Total exposure + new trade ≤ MAX_PORTFOLIO_EXPOSURE  ($150)
  3. Today's P&L ≥ -MAX_DAILY_LOSS  ($10 loss limit — auto-shutdown on breach)
  4. VPN (tun0) is connected
  5. Last data feed update < 5 minutes ago (data freshness)
  6. Market does not resolve within 24 hours
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from config.settings import settings
from data.database import Database
from data.models import SystemEvent, TradeSignal
from network.vpn import check_vpn
from risk.portfolio import Portfolio
from utils.logger import get_logger

if TYPE_CHECKING:
    from copy_trading.executor import CopyExecutor
    from utils.notifications import Notifier

logger = get_logger(__name__)

# Position that has lost more than this fraction of entry value is stopped out
_STOP_LOSS_THRESHOLD = 0.50   # 50%

# Data feed is considered stale after this many seconds without an update
_STALE_DATA_SECONDS = 300     # 5 minutes

# Market must have at least this many seconds until resolution to be tradeable
_MIN_SECONDS_TO_RESOLVE = 86_400  # 24 hours

# Risk check loop interval
_CHECK_INTERVAL = 30   # seconds


class RiskManager:
    """
    Enforces all pre-trade and ongoing risk guardrails.

    Usage::

        risk = RiskManager(db, portfolio, executor, notifier)
        # pre-trade:
        if await risk.check_order(signal, size):
            trade = await executor.execute_signal(signal)
        # continuous loop:
        await risk.run()
    """

    def __init__(
        self,
        db: Database,
        portfolio: Portfolio,
        executor: "CopyExecutor | None" = None,
        notifier: "Notifier | None" = None,
    ) -> None:
        self._db = db
        self._portfolio = portfolio
        self._executor = executor
        self._notifier = notifier

        # Timestamp of the most recent successful data feed update.
        # Callers (e.g. WalletTracker) should call record_feed_update() after
        # each successful poll so this stays current.
        self._last_feed_update: datetime = datetime.now(timezone.utc)

        # Set to True by emergency_shutdown() to halt all trading
        self._shutdown: bool = False

    # ------------------------------------------------------------------
    # Feed freshness API
    # ------------------------------------------------------------------

    def record_feed_update(self) -> None:
        """Mark the data feed as up-to-date (call after each successful poll)."""
        self._last_feed_update = datetime.now(timezone.utc)

    @property
    def feed_is_stale(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self._last_feed_update).total_seconds()
        return elapsed > _STALE_DATA_SECONDS

    @property
    def seconds_since_feed(self) -> float:
        return (datetime.now(timezone.utc) - self._last_feed_update).total_seconds()

    # ------------------------------------------------------------------
    # Pre-trade check
    # ------------------------------------------------------------------

    async def check_order(self, signal: TradeSignal, size: float) -> bool:
        """
        Run all pre-trade guards.  Returns True only if ALL checks pass.

        Args:
            signal: The TradeSignal to be executed.
            size:   Our intended order size (USD / shares).

        Returns:
            True → trade is allowed.
            False → trade is blocked (reason logged).
        """
        if self._shutdown:
            logger.warning("check_order_blocked_shutdown", market_slug=signal.market_slug)
            return False

        # 1. VPN check
        if not await asyncio.to_thread(check_vpn):
            logger.warning("check_order_blocked_vpn", market_slug=signal.market_slug)
            await self._log_event("RISK_BREACH", "VPN disconnected — order blocked", "WARNING")
            return False

        # 2. Stale data check
        if self.feed_is_stale:
            logger.warning(
                "check_order_blocked_stale_data",
                market_slug=signal.market_slug,
                seconds_since_feed=round(self.seconds_since_feed),
            )
            await self._log_event(
                "RISK_BREACH",
                f"Stale data feed ({round(self.seconds_since_feed)}s) — order blocked",
                "WARNING",
            )
            return False

        # 3. Position per market check
        market_exposure = await self._market_exposure(signal.token_id)
        if market_exposure + (size * signal.current_price) > settings.max_position_per_market:
            logger.warning(
                "check_order_blocked_market_limit",
                market_slug=signal.market_slug,
                market_exposure=round(market_exposure, 2),
                new_size_usd=round(size * signal.current_price, 2),
                limit=settings.max_position_per_market,
            )
            return False

        # 4. Total portfolio exposure check
        total_exp = await self._portfolio.total_exposure()
        new_exposure = size * signal.current_price
        if total_exp + new_exposure > settings.max_portfolio_exposure:
            logger.warning(
                "check_order_blocked_portfolio_limit",
                market_slug=signal.market_slug,
                total_exposure=round(total_exp, 2),
                new_exposure=round(new_exposure, 2),
                limit=settings.max_portfolio_exposure,
            )
            return False

        # 5. Daily loss limit check
        today_pnl = await self._portfolio.daily_pnl()
        if today_pnl <= -settings.max_daily_loss:
            logger.error(
                "check_order_blocked_daily_loss",
                market_slug=signal.market_slug,
                today_pnl=round(today_pnl, 2),
                limit=settings.max_daily_loss,
            )
            await self._trigger_daily_loss_shutdown(today_pnl)
            return False

        # 6. Market resolution window check
        resolves_soon = await self._resolves_within_24h(signal.market_slug)
        if resolves_soon:
            logger.warning(
                "check_order_blocked_resolution",
                market_slug=signal.market_slug,
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Stop-loss enforcement
    # ------------------------------------------------------------------

    async def check_stop_losses(self) -> list[str]:
        """
        Close any open trade that has lost more than 50% of its entry value.

        Returns the list of trade IDs that were stopped out.
        """
        open_trades = await self._db.get_open_trades()
        stopped: list[str] = []

        for trade in open_trades:
            if trade.entry_price <= 0:
                continue

            loss_fraction = (trade.entry_price - trade.current_price) / trade.entry_price
            if trade.side.upper() in ("YES", "NO", "BUY"):
                loss_fraction = (trade.entry_price - trade.current_price) / trade.entry_price
            else:
                loss_fraction = (trade.current_price - trade.entry_price) / trade.entry_price

            if loss_fraction >= _STOP_LOSS_THRESHOLD:
                logger.warning(
                    "stop_loss_triggered",
                    trade_id=trade.id,
                    market_slug=trade.market_slug,
                    entry_price=trade.entry_price,
                    current_price=trade.current_price,
                    loss_pct=round(loss_fraction * 100, 1),
                )
                await self._log_event(
                    "RISK_BREACH",
                    f"Stop loss triggered: {trade.market_slug} "
                    f"({round(loss_fraction * 100, 1)}% loss)",
                    "WARNING",
                )
                if self._executor is not None:
                    await self._executor.close_position(trade.id)
                stopped.append(trade.id)

        return stopped

    # ------------------------------------------------------------------
    # Emergency shutdown
    # ------------------------------------------------------------------

    async def emergency_shutdown(self, reason: str = "manual") -> None:
        """
        Cancel all open orders, mark bot as shut down, send Telegram alert.

        After this call, check_order() will always return False.
        """
        self._shutdown = True
        logger.error("emergency_shutdown", reason=reason)

        # Cancel all open CLOB orders via the executor's order manager
        if self._executor is not None and hasattr(self._executor, "_om"):
            try:
                cancelled = await self._executor._om.cancel_all_open()
                logger.info("emergency_shutdown_cancelled_orders", count=cancelled)
            except Exception as exc:
                logger.error("emergency_shutdown_cancel_error", error=str(exc))

        await self._log_event(
            "BOT_STOP",
            f"Emergency shutdown triggered: {reason}",
            "CRITICAL",
        )

        if self._notifier is not None:
            try:
                await self._notifier.send(
                    f"🚨 EMERGENCY SHUTDOWN\nReason: {reason}",
                    severity="CRITICAL",
                )
            except Exception as exc:
                logger.error("emergency_shutdown_notify_error", error=str(exc))

    # ------------------------------------------------------------------
    # Continuous risk loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """
        Periodically (every 30s):
          • check stop losses on all open positions
          • verify VPN status
          • check daily loss limit and trigger shutdown if breached

        Runs until cancelled or emergency_shutdown() is called.
        """
        logger.info("risk_manager_started", interval=_CHECK_INTERVAL)
        try:
            while not self._shutdown:
                await asyncio.sleep(_CHECK_INTERVAL)
                try:
                    await self.check_stop_losses()
                    await self._periodic_daily_loss_check()
                    await self._periodic_vpn_check()
                except Exception as exc:
                    logger.error("risk_loop_error", error=str(exc))
        except asyncio.CancelledError:
            logger.info("risk_manager_cancelled")
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _market_exposure(self, token_id: str) -> float:
        """Sum of (size × current_price) for open trades on the same token."""
        open_trades = await self._db.get_open_trades()
        return sum(
            t.size * t.current_price
            for t in open_trades
            if t.token_id == token_id
        )

    async def _resolves_within_24h(self, market_slug: str) -> bool:
        """
        Return True if the market resolves within the next 24 hours.
        Uses cached market data; returns False (allow trade) if unknown.
        """
        market = await self._db.get_market_by_slug(market_slug)
        if market is None or not market.end_date:
            return False
        try:
            end_dt = datetime.fromisoformat(market.end_date.replace("Z", "+00:00"))
            remaining = (end_dt - datetime.now(timezone.utc)).total_seconds()
            return remaining < _MIN_SECONDS_TO_RESOLVE
        except (ValueError, AttributeError):
            return False

    async def _trigger_daily_loss_shutdown(self, today_pnl: float) -> None:
        """Initiate emergency shutdown when the daily loss limit is breached."""
        reason = (
            f"Daily loss limit breached: ${abs(today_pnl):.2f} "
            f"(limit ${settings.max_daily_loss:.2f})"
        )
        await self.emergency_shutdown(reason=reason)

    async def _periodic_daily_loss_check(self) -> None:
        today_pnl = await self._portfolio.daily_pnl()
        if today_pnl <= -settings.max_daily_loss:
            await self._trigger_daily_loss_shutdown(today_pnl)

    async def _periodic_vpn_check(self) -> None:
        vpn_ok = await asyncio.to_thread(check_vpn)
        if not vpn_ok:
            logger.warning("periodic_vpn_check_failed")
            await self._log_event(
                "RISK_BREACH",
                "VPN disconnected detected during periodic check",
                "WARNING",
            )
            if self._notifier is not None:
                try:
                    await self._notifier.send(
                        "⚠️ VPN disconnected — trading paused",
                        severity="WARNING",
                    )
                except Exception:
                    pass

    async def _log_event(
        self, event_type: str, message: str, severity: str
    ) -> None:
        try:
            await self._db.log_event(SystemEvent(
                id=None,
                event_type=event_type,
                message=message,
                severity=severity,
            ))
        except Exception as exc:
            logger.error("risk_log_event_error", error=str(exc))
