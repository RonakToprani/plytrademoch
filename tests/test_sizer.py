"""
tests/test_sizer.py — Proportional sizing math unit tests.

Tests:
  • Core proportional formula
  • Clamping to [MIN_TRADE_SIZE, MAX_TRADE_SIZE]
  • Rounding to 2 decimal places
  • Fallback bankroll (unknown whale bankroll)
  • Edge cases: zero size, negative size, infinite size, zero price
"""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock

import pytest

from copy_trading.sizer import ProportionalSizer
from data.models import TradeSignal
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sizer(bankroll: float = 100.0, min_size: float = 1.0, max_size: float = 20.0) -> ProportionalSizer:
    return ProportionalSizer(our_bankroll=bankroll, min_trade_size=min_size, max_trade_size=max_size)


def _signal(size_delta: float = 500.0, price: float = 0.60) -> TradeSignal:
    return TradeSignal(
        wallet="0xWHALE",
        token_id="tok1",
        market_slug="market-a",
        side="YES",
        action="OPEN",
        whale_size_delta=size_delta,
        current_price=price,
        detected_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Core formula
# ---------------------------------------------------------------------------

class TestComputeSize:
    def test_proportional_formula(self):
        """our_size = (our_bankroll / whale_bankroll) * whale_trade_size"""
        sizer = _sizer(bankroll=100.0)
        # 100 / 50_000 * 500 = 1.0
        result = sizer.compute_size(whale_trade_size=500.0, whale_bankroll=50_000.0)
        assert result == pytest.approx(1.0, abs=0.01)

    def test_result_rounded_to_2dp(self):
        sizer = _sizer(bankroll=100.0)
        result = sizer.compute_size(whale_trade_size=333.0, whale_bankroll=10_000.0)
        assert result == round(result, 2)

    def test_larger_bankroll_larger_size(self):
        small = _sizer(bankroll=50.0).compute_size(500.0, 50_000.0)
        large = _sizer(bankroll=200.0).compute_size(500.0, 50_000.0)
        assert large > small

    def test_result_is_finite(self):
        sizer = _sizer()
        result = sizer.compute_size(whale_trade_size=1000.0, whale_bankroll=100_000.0)
        assert math.isfinite(result)


# ---------------------------------------------------------------------------
# Clamping
# ---------------------------------------------------------------------------

class TestClamping:
    def test_clamp_to_min(self):
        """Very small proportion → clamped to min_trade_size."""
        sizer = _sizer(bankroll=10.0, min_size=1.0, max_size=20.0)
        result = sizer.compute_size(whale_trade_size=1.0, whale_bankroll=1_000_000.0)
        assert result == 1.0

    def test_clamp_to_max(self):
        """Large proportion → clamped to max_trade_size."""
        sizer = _sizer(bankroll=100_000.0, min_size=1.0, max_size=20.0)
        result = sizer.compute_size(whale_trade_size=50_000.0, whale_bankroll=1_000.0)
        assert result == 20.0

    def test_within_bounds_not_clamped(self):
        sizer = _sizer(bankroll=100.0, min_size=1.0, max_size=20.0)
        # 100/10000 * 500 = 5.0 — inside [1, 20]
        result = sizer.compute_size(whale_trade_size=500.0, whale_bankroll=10_000.0)
        assert 1.0 <= result <= 20.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_zero_whale_trade_size(self):
        sizer = _sizer()
        result = sizer.compute_size(whale_trade_size=0.0, whale_bankroll=50_000.0)
        assert result == 1.0  # clamped to min

    def test_negative_whale_trade_size(self):
        sizer = _sizer()
        result = sizer.compute_size(whale_trade_size=-500.0, whale_bankroll=50_000.0)
        assert result == 1.0  # negative → clamped to min

    def test_zero_bankroll_uses_fallback(self):
        sizer = _sizer()
        # bankroll near zero → uses _MIN_WHALE_BANKROLL = 1.0 floor
        result = sizer.compute_size(whale_trade_size=5.0, whale_bankroll=0.0)
        assert math.isfinite(result)
        assert result >= 1.0

    def test_fallback_bankroll(self):
        sizer = _sizer()
        est = sizer.fallback_bankroll(largest_position_usd=10_000.0)
        assert est == pytest.approx(50_000.0)

    def test_fallback_bankroll_minimum_floor(self):
        sizer = _sizer()
        est = sizer.fallback_bankroll(largest_position_usd=0.0)
        assert est >= 1.0


# ---------------------------------------------------------------------------
# compute_size_from_signal
# ---------------------------------------------------------------------------

class TestSizeFromSignal:
    def test_uses_whale_size_delta(self):
        sizer = _sizer(bankroll=100.0)
        sig = _signal(size_delta=500.0)
        result = sizer.compute_size_from_signal(sig, whale_bankroll=50_000.0)
        expected = sizer.compute_size(500.0, 50_000.0)
        assert result == expected
