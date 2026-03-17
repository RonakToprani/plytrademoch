"""
tests/test_risk.py — Risk limit enforcement unit tests.

Tests:
  • check_order() blocks when any single guard fails
  • check_order() passes when all guards pass
  • Daily loss shutdown trigger
  • check_stop_losses() closes positions >50% loss
  • Feed staleness detection
  • VPN check integration
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from data.models import CopyTrade, TradeSignal
from risk.manager import RiskManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _signal(price: float = 0.60, market_slug: str = "market-a") -> TradeSignal:
    return TradeSignal(
        wallet="0xWHALE",
        token_id="tok1",
        market_slug=market_slug,
        side="YES",
        action="OPEN",
        whale_size_delta=500.0,
        current_price=price,
        detected_at=datetime.now(timezone.utc),
    )


def _open_trade(
    trade_id: str = "t1",
    entry: float = 0.60,
    current: float = 0.60,
    size: float = 5.0,
    token_id: str = "tok1",
) -> CopyTrade:
    return CopyTrade(
        id=trade_id,
        source_wallet="0xWHALE",
        market_slug="market-a",
        token_id=token_id,
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


def _make_risk(
    *,
    today_pnl: float = 0.0,
    total_exposure: float = 0.0,
    vpn_ok: bool = True,
    feed_stale: bool = False,
    market_expires_soon: bool = False,
) -> tuple[RiskManager, MagicMock, MagicMock]:
    db = MagicMock()
    portfolio = MagicMock()
    portfolio.daily_pnl = AsyncMock(return_value=today_pnl)
    portfolio.total_exposure = AsyncMock(return_value=total_exposure)

    db.get_open_trades = AsyncMock(return_value=[])
    db.get_market_by_slug = AsyncMock(return_value=None)
    db.log_event = AsyncMock()

    risk = RiskManager(db=db, portfolio=portfolio)
    if feed_stale:
        risk._last_feed_update = datetime.now(timezone.utc) - timedelta(seconds=400)

    return risk, db, portfolio


# ---------------------------------------------------------------------------
# check_order
# ---------------------------------------------------------------------------

class TestCheckOrder:
    @pytest.mark.asyncio
    async def test_passes_all_guards(self):
        risk, db, portfolio = _make_risk(today_pnl=2.0, total_exposure=50.0)
        with patch("risk.manager.check_vpn", return_value=True):
            result = await risk.check_order(_signal(), size=5.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_blocked_when_shutdown(self):
        risk, db, portfolio = _make_risk()
        risk._shutdown = True
        with patch("risk.manager.check_vpn", return_value=True):
            result = await risk.check_order(_signal(), size=5.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_blocked_vpn_down(self):
        risk, db, portfolio = _make_risk()
        with patch("risk.manager.check_vpn", return_value=False):
            result = await risk.check_order(_signal(), size=5.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_blocked_stale_feed(self):
        risk, db, portfolio = _make_risk(feed_stale=True)
        with patch("risk.manager.check_vpn", return_value=True):
            result = await risk.check_order(_signal(), size=5.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_blocked_portfolio_exposure_exceeded(self):
        risk, db, portfolio = _make_risk(total_exposure=148.0)
        with patch("risk.manager.check_vpn", return_value=True):
            # 148 + (5 * 0.60 = 3) = 151 > 150
            result = await risk.check_order(_signal(price=0.60), size=5.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_blocked_daily_loss_limit(self):
        risk, db, portfolio = _make_risk(today_pnl=-10.0)
        with patch("risk.manager.check_vpn", return_value=True):
            result = await risk.check_order(_signal(), size=1.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_blocked_market_per_position_limit(self):
        risk, db, portfolio = _make_risk(total_exposure=10.0)
        # Existing $18 in this market → adding $5 would exceed $20 limit
        trade = _open_trade(token_id="tok1", size=30.0, current=0.60)  # 30 * 0.60 = $18
        db.get_open_trades = AsyncMock(return_value=[trade])
        with patch("risk.manager.check_vpn", return_value=True):
            result = await risk.check_order(_signal(price=0.60), size=5.0)
        assert result is False


# ---------------------------------------------------------------------------
# Feed staleness
# ---------------------------------------------------------------------------

class TestFeedStaleness:
    def test_fresh_feed_not_stale(self):
        risk, _, _ = _make_risk()
        assert not risk.feed_is_stale

    def test_stale_feed(self):
        risk, _, _ = _make_risk(feed_stale=True)
        assert risk.feed_is_stale

    def test_record_feed_update_clears_staleness(self):
        risk, _, _ = _make_risk(feed_stale=True)
        risk.record_feed_update()
        assert not risk.feed_is_stale


# ---------------------------------------------------------------------------
# Stop losses
# ---------------------------------------------------------------------------

class TestStopLosses:
    @pytest.mark.asyncio
    async def test_stop_loss_triggered_at_50_pct(self):
        risk, db, portfolio = _make_risk()
        # Entry 0.60, current 0.29 → 51.7% loss
        trade = _open_trade(entry=0.60, current=0.29)
        db.get_open_trades = AsyncMock(return_value=[trade])

        executor = MagicMock()
        executor.close_position = AsyncMock()
        risk._executor = executor

        stopped = await risk.check_stop_losses()
        assert "t1" in stopped
        executor.close_position.assert_awaited_once_with("t1")

    @pytest.mark.asyncio
    async def test_no_stop_loss_within_threshold(self):
        risk, db, portfolio = _make_risk()
        # Entry 0.60, current 0.40 → 33% loss (below 50%)
        trade = _open_trade(entry=0.60, current=0.40)
        db.get_open_trades = AsyncMock(return_value=[trade])
        executor = MagicMock()
        executor.close_position = AsyncMock()
        risk._executor = executor

        stopped = await risk.check_stop_losses()
        assert stopped == []
        executor.close_position.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_open_trades(self):
        risk, db, portfolio = _make_risk()
        db.get_open_trades = AsyncMock(return_value=[])
        stopped = await risk.check_stop_losses()
        assert stopped == []
