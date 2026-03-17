"""
copy_trading/executor.py — Copy trade execution pipeline.

Responsibilities:
  • execute_signal(signal)         — full pipeline: size → risk check → place/simulate → save → notify
  • close_position(trade_id)       — exit a position when the whale exits
  • handle_detection_batch(signals)— process a batch of signals from one poll cycle
  • run(signal_queue)              — async loop consuming TradeSignals from the detector

Pipeline (per signal):
  1. Compute size via ProportionalSizer
  2. Risk check via RiskManager.check_order()          [imported lazily to avoid circular deps]
  3a. DRY_RUN: simulate fill at current mid price, save CopyTrade with status=FILLED
  3b. Live:    place limit order at (mid + 0.01) via OrderManager
  4. Save CopyTrade to database
  5. Send Telegram notification

Action mapping:
  OPEN / INCREASE / FLIP  →  execute_signal (BUY our side)
  DECREASE / CLOSE        →  close_position (exit our mirroring trade)
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from config.settings import settings
from copy_trading.sizer import ProportionalSizer
from core.order_manager import OrderManager
from data.database import Database
from data.models import CopyTrade, SystemEvent, TradeSignal
from utils.logger import bind_trade_context, clear_context, get_logger

if TYPE_CHECKING:
    from risk.manager import RiskManager
    from utils.notifications import Notifier

logger = get_logger(__name__)

# Signals that represent entering (or adding to) a position
_ENTRY_ACTIONS = {"OPEN", "INCREASE", "FLIP"}
# Signals that represent exiting a position
_EXIT_ACTIONS = {"DECREASE", "CLOSE"}

# Limit price offset above mid for fast fills on BUY orders
_PRICE_SLIPPAGE = 0.01


class CopyExecutor:
    """
    Executes copy trades in response to whale TradeSignals.

    Usage::

        executor = CopyExecutor(db, order_manager, risk_manager, notifier)
        # consume a single signal:
        trade = await executor.execute_signal(signal)
        # or run the continuous loop:
        queue: asyncio.Queue[TradeSignal] = asyncio.Queue()
        await executor.run(queue)
    """

    def __init__(
        self,
        db: Database,
        order_manager: OrderManager,
        risk_manager: "RiskManager | None" = None,
        notifier: "Notifier | None" = None,
    ) -> None:
        self._db = db
        self._om = order_manager
        self._risk = risk_manager
        self._notifier = notifier
        self._sizer = ProportionalSizer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute_signal(self, signal: TradeSignal) -> CopyTrade | None:
        """
        Full execution pipeline for a single TradeSignal.

        Entry signals (OPEN / INCREASE / FLIP) are processed as new BUY orders.
        Exit signals (DECREASE / CLOSE) delegate to close_position().

        Returns the saved CopyTrade on success, or None if blocked/skipped.
        """
        if signal.action in _EXIT_ACTIONS:
            return await self._handle_exit_signal(signal)

        if signal.action not in _ENTRY_ACTIONS:
            logger.warning("unknown_signal_action", action=signal.action)
            return None

        trade_id = str(uuid.uuid4())
        bind_trade_context(trade_id)

        try:
            # Step 1: size
            our_size = await self._sizer.size_for_signal(signal, self._db)

            # Step 2: risk check
            if self._risk is not None:
                allowed = await self._risk.check_order(signal, our_size)
                if not allowed:
                    logger.info(
                        "signal_blocked_by_risk",
                        trade_id=trade_id,
                        market_slug=signal.market_slug,
                        action=signal.action,
                    )
                    return None

            # Step 3a / 3b: place or simulate
            entry_price, status, filled_at = await self._fill_or_simulate(
                signal=signal,
                trade_id=trade_id,
                our_size=our_size,
            )

            # Step 4: persist
            trade = CopyTrade(
                id=trade_id,
                source_wallet=signal.wallet,
                market_slug=signal.market_slug,
                token_id=signal.token_id,
                side=signal.side,
                size=our_size,
                whale_size=signal.whale_size_delta,
                entry_price=entry_price,
                current_price=signal.current_price,
                pnl=0.0,
                status=status,
                created_at=datetime.now(timezone.utc),
                filled_at=filled_at,
            )
            await self._db.save_trade(trade)

            # Step 5: notify
            await self._notify_trade_opened(trade)

            logger.info(
                "copy_trade_executed",
                trade_id=trade_id,
                market_slug=signal.market_slug,
                side=signal.side,
                size=our_size,
                entry_price=entry_price,
                status=status,
                dry_run=settings.dry_run,
            )
            return trade

        except Exception as exc:
            logger.error(
                "execute_signal_error",
                trade_id=trade_id,
                market_slug=signal.market_slug,
                error=str(exc),
            )
            await self._db.log_event(SystemEvent(
                id=None,
                event_type="ERROR",
                message=f"execute_signal failed for {signal.market_slug}: {exc}",
                severity="ERROR",
            ))
            return None
        finally:
            clear_context()

    async def close_position(self, trade_id: str) -> bool:
        """
        Close an open copy trade (whale has exited — we exit too).

        In DRY_RUN mode: marks the trade as CLOSED and computes final P&L
        using the current_price from the most recent DB snapshot.

        In live mode: places a SELL order via OrderManager.

        Returns True on success, False if the trade was not found or already closed.
        """
        trade = await self._db.get_trade(trade_id)
        if trade is None:
            logger.warning("close_position_not_found", trade_id=trade_id)
            return False
        if trade.status == "CLOSED":
            logger.debug("close_position_already_closed", trade_id=trade_id)
            return False

        bind_trade_context(trade_id)
        try:
            if settings.dry_run:
                pnl = _compute_pnl(trade.side, trade.size, trade.entry_price, trade.current_price)
                await self._db.update_trade(
                    trade_id,
                    pnl=pnl,
                    status="CLOSED",
                    filled_at=datetime.now(timezone.utc),
                )
                logger.info(
                    "position_closed_simulated",
                    trade_id=trade_id,
                    market_slug=trade.market_slug,
                    exit_price=trade.current_price,
                    pnl=round(pnl, 4),
                )
            else:
                # SELL our position back on the CLOB
                exit_side = "SELL"
                exit_price = max(0.01, round(trade.current_price - _PRICE_SLIPPAGE, 2))
                result = await self._om.place_order(
                    token_id=trade.token_id,
                    side=exit_side,
                    size=trade.size,
                    price=exit_price,
                )
                pnl = _compute_pnl(trade.side, trade.size, trade.entry_price, exit_price)
                await self._db.update_trade(
                    trade_id,
                    pnl=pnl,
                    status="CLOSED",
                    filled_at=datetime.now(timezone.utc),
                )
                logger.info(
                    "position_closed_live",
                    trade_id=trade_id,
                    market_slug=trade.market_slug,
                    order_id=result.get("orderID"),
                    exit_price=exit_price,
                    pnl=round(pnl, 4),
                )

            await self._notify_trade_closed(trade, pnl)
            return True

        except Exception as exc:
            logger.error(
                "close_position_error",
                trade_id=trade_id,
                error=str(exc),
            )
            return False
        finally:
            clear_context()

    async def handle_detection_batch(self, signals: list[TradeSignal]) -> list[CopyTrade]:
        """
        Process all signals emitted from a single poll cycle sequentially.

        Returns the list of successfully executed CopyTrade objects.
        """
        if not signals:
            return []

        results: list[CopyTrade] = []
        for signal in signals:
            trade = await self.execute_signal(signal)
            if trade is not None:
                results.append(trade)
        return results

    async def run(self, signal_queue: asyncio.Queue[TradeSignal]) -> None:
        """
        Continuously consume TradeSignals from *signal_queue* and execute
        them.  Runs until cancelled.
        """
        logger.info("copy_executor_started", dry_run=settings.dry_run)
        try:
            while True:
                signal = await signal_queue.get()
                try:
                    await self.execute_signal(signal)
                except Exception as exc:
                    logger.error(
                        "executor_loop_error",
                        market_slug=signal.market_slug,
                        error=str(exc),
                    )
                finally:
                    signal_queue.task_done()
        except asyncio.CancelledError:
            logger.info("copy_executor_cancelled")
            raise

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fill_or_simulate(
        self,
        signal: TradeSignal,
        trade_id: str,
        our_size: float,
    ) -> tuple[float, str, datetime | None]:
        """
        Either simulate a fill (DRY_RUN) or place a live limit order.

        Returns:
            (entry_price, status, filled_at)
        """
        if settings.dry_run:
            # Simulate fill at current mid price
            entry_price = signal.current_price
            status = "FILLED"
            filled_at = datetime.now(timezone.utc)
            logger.info(
                "paper_trade_simulated",
                trade_id=trade_id,
                market_slug=signal.market_slug,
                side=signal.side,
                size=our_size,
                simulated_price=entry_price,
            )
            return entry_price, status, filled_at

        # Live: place limit order slightly above mid for fast fill
        limit_price = min(0.99, round(signal.current_price + _PRICE_SLIPPAGE, 2))
        result = await self._om.place_order(
            token_id=signal.token_id,
            side="BUY",
            size=our_size,
            price=limit_price,
        )
        entry_price = limit_price
        status = "PENDING"
        filled_at = None
        return entry_price, status, filled_at

    async def _handle_exit_signal(self, signal: TradeSignal) -> CopyTrade | None:
        """
        Find the open trade that mirrors *signal*'s token and close it.

        Looks for an open FILLED/PARTIAL trade on the same token_id from the
        same source wallet.
        """
        open_trades = await self._db.get_open_trades()
        matching = [
            t for t in open_trades
            if t.token_id == signal.token_id
            and t.source_wallet == signal.wallet
            and t.status in ("FILLED", "PARTIAL")
        ]

        if not matching:
            logger.debug(
                "exit_signal_no_matching_trade",
                token_id=signal.token_id[:12],
                market_slug=signal.market_slug,
                action=signal.action,
            )
            return None

        # Close the oldest matching position
        target = min(matching, key=lambda t: t.created_at)
        success = await self.close_position(target.id)
        if success:
            return await self._db.get_trade(target.id)
        return None

    async def _notify_trade_opened(self, trade: CopyTrade) -> None:
        if self._notifier is None:
            return
        mode = "PAPER" if settings.dry_run else "LIVE"
        msg = (
            f"[{mode}] Copy trade opened\n"
            f"Market: {trade.market_slug}\n"
            f"Side: {trade.side}  Size: {trade.size:.2f}\n"
            f"Entry: {trade.entry_price:.3f}\n"
            f"Source: {trade.source_wallet[:10]}…"
        )
        try:
            await self._notifier.send(msg, severity="INFO")
        except Exception as exc:
            logger.warning("notify_trade_opened_failed", error=str(exc))

    async def _notify_trade_closed(self, trade: CopyTrade, pnl: float) -> None:
        if self._notifier is None:
            return
        mode = "PAPER" if settings.dry_run else "LIVE"
        sign = "+" if pnl >= 0 else ""
        msg = (
            f"[{mode}] Copy trade closed\n"
            f"Market: {trade.market_slug}\n"
            f"Side: {trade.side}  Size: {trade.size:.2f}\n"
            f"P&L: {sign}{pnl:.2f} USD"
        )
        try:
            await self._notifier.send(msg, severity="INFO")
        except Exception as exc:
            logger.warning("notify_trade_closed_failed", error=str(exc))


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _compute_pnl(side: str, size: float, entry_price: float, exit_price: float) -> float:
    """
    Compute realised P&L for a closed position.

    For a BUY (long YES/NO token):
        pnl = size * (exit_price - entry_price)

    For a SELL (short):
        pnl = size * (entry_price - exit_price)
    """
    if side.upper() in ("YES", "NO", "BUY"):
        return round(size * (exit_price - entry_price), 4)
    return round(size * (entry_price - exit_price), 4)
