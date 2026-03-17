"""
tests/test_executor.py — Order placement and copy trade execution unit tests.

Tests:
  • DRY_RUN: simulate fill at mid price, save CopyTrade with FILLED status
  • DRY_RUN: execute_signal returns CopyTrade with correct fields
  • Risk check blocks signal when check_order returns False
  • Exit signal (DECREASE/CLOSE) routes to close_position
  • close_position: DRY_RUN marks CLOSED, computes P&L
  • handle_detection_batch: processes all signals, returns results
  • _compute_pnl helper correctness
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from copy_trading.executor import CopyExecutor, _compute_pnl
from data.models import CopyTrade, TradeSignal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _signal(action: str = "OPEN", price: float = 0.60, token_id: str = "tok1") -> TradeSignal:
    return TradeSignal(
        wallet="0xWHALE",
        token_id=token_id,
        market_slug="market-a",
        side="YES",
        action=action,
        whale_size_delta=500.0,
        current_price=price,
        detected_at=datetime.now(timezone.utc),
    )


def _filled_trade(trade_id: str = "t1", entry: float = 0.60, current: float = 0.60, size: float = 5.0) -> CopyTrade:
    return CopyTrade(
        id=trade_id,
        source_wallet="0xWHALE",
        market_slug="market-a",
        token_id="tok1",
        side="YES",
        size=size,
        whale_size=50.0,
        entry_price=entry,
        current_price=current,
        pnl=0.0,
        status="FILLED",
        created_at=datetime.now(timezone.utc),
        filled_at=datetime.now(timezone.utc),
    )


def _make_executor(*, dry_run: bool = True, risk_allows: bool = True) -> tuple[CopyExecutor, MagicMock, MagicMock]:
    db = MagicMock()
    db.save_trade = AsyncMock()
    db.update_trade = AsyncMock()
    db.get_trade = AsyncMock(return_value=None)
    db.get_open_trades = AsyncMock(return_value=[])
    db.log_event = AsyncMock()
    db.get_wallet = AsyncMock(return_value=None)

    order_manager = MagicMock()
    order_manager.place_order = AsyncMock(return_value={"orderID": "order-123"})

    risk = MagicMock()
    risk.check_order = AsyncMock(return_value=risk_allows)

    notifier = MagicMock()
    notifier.send = AsyncMock()

    executor = CopyExecutor(db=db, order_manager=order_manager, risk_manager=risk, notifier=notifier)

    with patch("copy_trading.executor.settings") as mock_settings:
        mock_settings.dry_run = dry_run
        mock_settings.bankroll = 100.0
        mock_settings.min_trade_size = 1.0
        mock_settings.max_trade_size = 20.0

    return executor, db, order_manager


# ---------------------------------------------------------------------------
# DRY_RUN execution
# ---------------------------------------------------------------------------

class TestDryRunExecution:
    @pytest.mark.asyncio
    async def test_dry_run_returns_filled_trade(self):
        executor, db, om = _make_executor(dry_run=True)
        with patch("copy_trading.executor.settings") as s:
            s.dry_run = True
            trade = await executor.execute_signal(_signal())
        assert trade is not None
        assert trade.status == "FILLED"
        assert trade.entry_price == pytest.approx(0.60)
        db.save_trade.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dry_run_does_not_call_order_manager(self):
        executor, db, om = _make_executor(dry_run=True)
        with patch("copy_trading.executor.settings") as s:
            s.dry_run = True
            await executor.execute_signal(_signal())
        om.place_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_risk_block_returns_none(self):
        executor, db, om = _make_executor(dry_run=True, risk_allows=False)
        with patch("copy_trading.executor.settings") as s:
            s.dry_run = True
            trade = await executor.execute_signal(_signal())
        assert trade is None
        db.save_trade.assert_not_awaited()


# ---------------------------------------------------------------------------
# Exit signal routing
# ---------------------------------------------------------------------------

class TestExitSignal:
    @pytest.mark.asyncio
    async def test_decrease_routes_to_close_position(self):
        executor, db, om = _make_executor(dry_run=True)
        trade = _filled_trade()
        db.get_open_trades = AsyncMock(return_value=[trade])
        db.get_trade = AsyncMock(return_value=trade)

        with patch("copy_trading.executor.settings") as s:
            s.dry_run = True
            await executor.execute_signal(_signal(action="DECREASE"))

        db.update_trade.assert_awaited()

    @pytest.mark.asyncio
    async def test_no_matching_trade_for_exit(self):
        executor, db, om = _make_executor(dry_run=True)
        db.get_open_trades = AsyncMock(return_value=[])
        with patch("copy_trading.executor.settings") as s:
            s.dry_run = True
            result = await executor.execute_signal(_signal(action="CLOSE"))
        assert result is None


# ---------------------------------------------------------------------------
# close_position
# ---------------------------------------------------------------------------

class TestClosePosition:
    @pytest.mark.asyncio
    async def test_dry_run_marks_closed(self):
        executor, db, om = _make_executor(dry_run=True)
        trade = _filled_trade(entry=0.60, current=0.75)
        db.get_trade = AsyncMock(return_value=trade)

        with patch("copy_trading.executor.settings") as s:
            s.dry_run = True
            success = await executor.close_position("t1")

        assert success is True
        call_kwargs = db.update_trade.call_args
        assert call_kwargs.kwargs["status"] == "CLOSED"

    @pytest.mark.asyncio
    async def test_close_nonexistent_trade_returns_false(self):
        executor, db, om = _make_executor(dry_run=True)
        db.get_trade = AsyncMock(return_value=None)
        with patch("copy_trading.executor.settings") as s:
            s.dry_run = True
            result = await executor.close_position("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_close_already_closed_returns_false(self):
        executor, db, om = _make_executor(dry_run=True)
        trade = _filled_trade()
        trade.status = "CLOSED"
        db.get_trade = AsyncMock(return_value=trade)
        with patch("copy_trading.executor.settings") as s:
            s.dry_run = True
            result = await executor.close_position("t1")
        assert result is False


# ---------------------------------------------------------------------------
# handle_detection_batch
# ---------------------------------------------------------------------------

class TestHandleDetectionBatch:
    @pytest.mark.asyncio
    async def test_empty_batch_returns_empty(self):
        executor, db, om = _make_executor(dry_run=True)
        with patch("copy_trading.executor.settings") as s:
            s.dry_run = True
            result = await executor.handle_detection_batch([])
        assert result == []

    @pytest.mark.asyncio
    async def test_batch_processes_all_signals(self):
        executor, db, om = _make_executor(dry_run=True)
        signals = [_signal(token_id=f"tok{i}") for i in range(3)]
        with patch("copy_trading.executor.settings") as s:
            s.dry_run = True
            results = await executor.handle_detection_batch(signals)
        assert len(results) == 3


# ---------------------------------------------------------------------------
# _compute_pnl
# ---------------------------------------------------------------------------

class TestComputePnl:
    def test_long_profit(self):
        pnl = _compute_pnl("YES", 100.0, 0.40, 0.70)
        assert pnl == pytest.approx(30.0, abs=0.001)

    def test_long_loss(self):
        pnl = _compute_pnl("YES", 100.0, 0.70, 0.40)
        assert pnl == pytest.approx(-30.0, abs=0.001)

    def test_buy_side_long_profit(self):
        pnl = _compute_pnl("BUY", 10.0, 0.50, 0.80)
        assert pnl == pytest.approx(3.0, abs=0.001)

    def test_zero_size(self):
        pnl = _compute_pnl("YES", 0.0, 0.50, 0.80)
        assert pnl == pytest.approx(0.0)
