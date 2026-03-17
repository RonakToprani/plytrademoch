"""
main.py — Async orchestrator for the Polymarket copy trading bot.

Start sequence:
  1. Load config from .env
  2. Init database (create tables)
  3. Init PolymarketClient (CLOB + Gamma + Data API auth)
  4. Check VPN status
  5. Check USDC balance
  6. Run initial wallet scan (or load from DB)
  7. Start Dash dashboard on a daemon thread
  8. Launch async tasks:
       a. WalletTracker.run()        — poll positions every 30s
       b. TradeDetector.run()        — detect changes, push to signal_queue
       c. CopyExecutor.run()         — consume signals, execute/simulate trades
       d. RiskManager.run()          — check stop losses, exposure, daily P&L every 30s
       e. Portfolio mark-to-market   — every 60s
       f. Daily wallet rescan        — every 24h
       g. Daily P&L snapshot         — at midnight UTC
  9. Graceful shutdown on SIGINT/SIGTERM:
       - Cancel all open orders
       - Save final state to DB
       - Send Telegram shutdown notification

Usage:
    python main.py
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
import threading
from datetime import datetime, timezone

from config.settings import settings
from copy_trading.detector import TradeDetector
from copy_trading.executor import CopyExecutor
from copy_trading.scanner import WalletScanner
from copy_trading.tracker import WalletTracker
from core.client import PolymarketClient
from core.order_manager import OrderManager
from core.wallet import create_authenticated_client
from data.database import Database
from data.models import SystemEvent, TradeSignal
from network.vpn import check_vpn, get_public_ip
from risk.manager import RiskManager
from risk.portfolio import Portfolio
from utils.logger import configure_logging, get_logger
from utils.notifications import Notifier

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MARK_TO_MARKET_INTERVAL = 60   # seconds
_DAILY_RESCAN_INTERVAL = 86_400  # 24 hours
_MIDNIGHT_CHECK_INTERVAL = 60   # how often to check if it's midnight


# ---------------------------------------------------------------------------
# Task helpers
# ---------------------------------------------------------------------------

async def _mark_to_market_loop(portfolio: Portfolio) -> None:
    """Update current prices and unrealized P&L every 60 seconds."""
    while True:
        await asyncio.sleep(_MARK_TO_MARKET_INTERVAL)
        try:
            await portfolio.mark_to_market()
        except Exception as exc:
            logger.error("mark_to_market_loop_error", error=str(exc))


async def _daily_rescan_loop(scanner: WalletScanner) -> None:
    """Re-score all tracked wallets every 24 hours."""
    while True:
        await asyncio.sleep(_DAILY_RESCAN_INTERVAL)
        try:
            logger.info("daily_rescan_started")
            await scanner.rescan_all()
        except Exception as exc:
            logger.error("daily_rescan_error", error=str(exc))


async def _midnight_pnl_snapshot_loop(portfolio: Portfolio, notifier: Notifier) -> None:
    """
    At midnight UTC: snapshot daily P&L, send Telegram daily report.
    Checks every minute whether the current hour/minute == 00:00 UTC.
    """
    last_snapshot_date: str | None = None
    while True:
        await asyncio.sleep(_MIDNIGHT_CHECK_INTERVAL)
        now = datetime.now(timezone.utc)
        today = now.date().isoformat()
        if now.hour == 0 and now.minute == 0 and today != last_snapshot_date:
            try:
                record = await portfolio.snapshot_daily_pnl()
                last_snapshot_date = today
                await notifier.daily_report(
                    total_pnl=record.total_pnl,
                    today_pnl=record.realized_pnl,
                    num_trades=record.num_trades,
                    win_rate=record.win_rate,
                    exposure=record.total_exposure,
                )
            except Exception as exc:
                logger.error("midnight_snapshot_error", error=str(exc))


def _start_dashboard() -> threading.Thread:
    """Start the Dash dashboard on a daemon thread."""
    from dashboard.app import create_app

    app = create_app()

    def _run() -> None:
        app.run(
            host="0.0.0.0",
            port=settings.dashboard_port,
            debug=False,
            use_reloader=False,
        )

    thread = threading.Thread(target=_run, name="dashboard", daemon=True)
    thread.start()
    logger.info("dashboard_started", port=settings.dashboard_port)
    return thread


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    configure_logging()
    logger.info("copybot_starting", dry_run=settings.dry_run)

    # ------------------------------------------------------------------
    # Step 1-2: Database
    # ------------------------------------------------------------------
    db = Database()
    await db.open()

    notifier = Notifier()

    try:
        await db.log_event(SystemEvent(
            id=None, event_type="BOT_START",
            message=f"CopyBot starting — dry_run={settings.dry_run}",
            severity="INFO",
        ))

        # ------------------------------------------------------------------
        # Step 3: Polymarket client
        # ------------------------------------------------------------------
        clob_client = await create_authenticated_client()
        pm_client = PolymarketClient(clob_client)
        await pm_client.__aenter__()

        # ------------------------------------------------------------------
        # Step 4: VPN check
        # ------------------------------------------------------------------
        vpn_ok = check_vpn()
        if not vpn_ok:
            logger.warning("vpn_not_detected", note="Trading will be blocked until VPN is up")
        else:
            public_ip = get_public_ip()
            logger.info("vpn_ok", public_ip=public_ip)

        # ------------------------------------------------------------------
        # Step 5: USDC balance
        # ------------------------------------------------------------------
        try:
            from core.wallet import get_usdc_balance
            balance = await get_usdc_balance(clob_client)
            logger.info("usdc_balance", balance_usd=balance)
        except Exception as exc:
            logger.warning("balance_check_failed", error=str(exc))

        # ------------------------------------------------------------------
        # Step 6: Wallet scan / load
        # ------------------------------------------------------------------
        scanner = WalletScanner(pm_client, db)
        active_wallets = await db.get_active_wallets()
        if active_wallets:
            logger.info("loaded_wallets_from_db", count=len(active_wallets))
        else:
            logger.info("initial_wallet_scan_starting")
            try:
                await scanner.discover_wallets()
            except Exception as exc:
                logger.warning("initial_wallet_scan_failed", error=str(exc))

        # ------------------------------------------------------------------
        # Step 7: Dashboard
        # ------------------------------------------------------------------
        _start_dashboard()

        # ------------------------------------------------------------------
        # Step 8: Build core objects
        # ------------------------------------------------------------------
        order_manager = OrderManager(pm_client)
        portfolio = Portfolio(db, pm_client)

        risk_manager = RiskManager(db, portfolio, notifier=notifier)
        tracker = WalletTracker(pm_client, db)
        detector = TradeDetector(db)
        executor = CopyExecutor(db, order_manager, risk_manager=risk_manager, notifier=notifier)

        # Wire executor back into risk_manager for emergency shutdown
        risk_manager._executor = executor

        # Signal queue connecting detector → executor
        signal_queue: asyncio.Queue[TradeSignal] = asyncio.Queue(maxsize=500)

        await notifier.bot_started(settings.dry_run)

        # ------------------------------------------------------------------
        # Step 8: Launch async tasks
        # ------------------------------------------------------------------
        async def _tracker_with_feed_updates() -> None:
            """Wrap tracker.run(), calling record_feed_update after each poll cycle."""
            while True:
                wallets = await db.get_active_wallets()
                if wallets:
                    for w in wallets:
                        await tracker.take_snapshot(w.address)
                    risk_manager.record_feed_update()
                await asyncio.sleep(settings.poll_interval_seconds)

        tasks = [
            asyncio.create_task(_tracker_with_feed_updates(), name="tracker"),
            asyncio.create_task(detector.run(signal_queue), name="detector"),
            asyncio.create_task(executor.run(signal_queue), name="executor"),
            asyncio.create_task(risk_manager.run(), name="risk_manager"),
            asyncio.create_task(order_manager.run_reconcile_loop(), name="reconcile"),
            asyncio.create_task(_mark_to_market_loop(portfolio), name="mark_to_market"),
            asyncio.create_task(_daily_rescan_loop(scanner), name="daily_rescan"),
            asyncio.create_task(_midnight_pnl_snapshot_loop(portfolio, notifier), name="midnight_snapshot"),
        ]

        logger.info("all_tasks_started", count=len(tasks))

        # ------------------------------------------------------------------
        # Step 9: Wait — cancel on SIGINT/SIGTERM
        # ------------------------------------------------------------------
        stop_event = asyncio.Event()

        def _handle_signal(sig: signal.Signals) -> None:
            logger.info("shutdown_signal_received", signal=sig.name)
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: _handle_signal(s))

        await stop_event.wait()

    except Exception as exc:
        logger.critical("main_unhandled_error", error=str(exc), exc_info=True)
        raise

    finally:
        logger.info("shutdown_started")

        # Cancel all tasks
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        # Cancel all open orders
        try:
            cancelled = await order_manager.cancel_all_open()
            logger.info("shutdown_orders_cancelled", count=cancelled)
        except Exception as exc:
            logger.error("shutdown_cancel_error", error=str(exc))

        # Final P&L snapshot
        try:
            await portfolio.snapshot_daily_pnl()
        except Exception as exc:
            logger.error("shutdown_snapshot_error", error=str(exc))

        # Telegram notification
        await notifier.bot_stopped(reason="graceful shutdown")

        # Close HTTP client and DB
        try:
            await pm_client.__aexit__(None, None, None)
        except Exception:
            pass
        await db.log_event(SystemEvent(
            id=None, event_type="BOT_STOP",
            message="CopyBot stopped — graceful shutdown",
            severity="INFO",
        ))
        await db.close()
        logger.info("shutdown_complete")


if __name__ == "__main__":
    asyncio.run(main())
