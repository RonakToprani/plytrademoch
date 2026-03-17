"""
tests/test_detector.py — Trade detection (snapshot diffing) unit tests.

Tests:
  • New position (OPEN)
  • Increased position (INCREASE)
  • Decreased position (DECREASE)
  • Closed position (CLOSE)
  • Side flip (FLIP)
  • Delta-neutral filtering (both YES and NO on same market)
  • Sub-$100 delta filtering
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from copy_trading.detector import (
    ACTION_CLOSE,
    ACTION_DECREASE,
    ACTION_FLIP,
    ACTION_INCREASE,
    ACTION_OPEN,
    TradeDetector,
)
from data.models import WalletSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snap(token_id: str, side: str, size: float, price: float = 0.60, slug: str = "market-a") -> WalletSnapshot:
    return WalletSnapshot(
        wallet_address="0xWHALE",
        token_id=token_id,
        market_slug=slug,
        side=side,
        size=size,
        avg_entry_price=price,
        current_price=price,
        timestamp=datetime.now(timezone.utc),
    )


def _detector() -> TradeDetector:
    db = MagicMock()
    return TradeDetector(db)


# ---------------------------------------------------------------------------
# Core diff logic
# ---------------------------------------------------------------------------

class TestDiffSnapshots:
    def test_new_position_is_open(self):
        d = _detector()
        old = []
        new = [_snap("tok1", "YES", 200.0, price=0.60)]
        signals = d._diff_snapshots("0xWHALE", old, new)
        assert len(signals) == 1
        assert signals[0].action == ACTION_OPEN
        assert signals[0].whale_size_delta == 200.0

    def test_increased_position(self):
        d = _detector()
        old = [_snap("tok1", "YES", 200.0)]
        new = [_snap("tok1", "YES", 350.0)]
        signals = d._diff_snapshots("0xWHALE", old, new)
        assert len(signals) == 1
        assert signals[0].action == ACTION_INCREASE
        assert signals[0].whale_size_delta == pytest.approx(150.0)

    def test_decreased_position(self):
        d = _detector()
        old = [_snap("tok1", "YES", 300.0)]
        new = [_snap("tok1", "YES", 100.0)]
        signals = d._diff_snapshots("0xWHALE", old, new)
        assert len(signals) == 1
        assert signals[0].action == ACTION_DECREASE
        assert signals[0].whale_size_delta == pytest.approx(200.0)

    def test_closed_position(self):
        d = _detector()
        old = [_snap("tok1", "YES", 300.0)]
        new = []
        signals = d._diff_snapshots("0xWHALE", old, new)
        assert len(signals) == 1
        assert signals[0].action == ACTION_CLOSE

    def test_side_flip(self):
        d = _detector()
        old = [_snap("tok1", "YES", 300.0)]
        new = [_snap("tok1", "NO", 300.0)]
        signals = d._diff_snapshots("0xWHALE", old, new)
        assert len(signals) == 1
        assert signals[0].action == ACTION_FLIP
        assert signals[0].side == "NO"

    def test_no_change_emits_nothing(self):
        d = _detector()
        snap = _snap("tok1", "YES", 300.0)
        signals = d._diff_snapshots("0xWHALE", [snap], [snap])
        assert signals == []

    def test_multiple_positions(self):
        d = _detector()
        old = [_snap("tok1", "YES", 100.0), _snap("tok2", "NO", 50.0)]
        new = [_snap("tok1", "YES", 200.0), _snap("tok3", "YES", 75.0)]
        signals = d._diff_snapshots("0xWHALE", old, new)
        actions = {s.token_id: s.action for s in signals}
        assert actions["tok1"] == ACTION_INCREASE   # increased
        assert actions["tok2"] == ACTION_CLOSE       # disappeared
        assert actions["tok3"] == ACTION_OPEN        # new


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

class TestFilterSignals:
    def test_small_delta_filtered(self):
        """Position change worth <$100 should be dropped."""
        d = _detector()
        old = [_snap("tok1", "YES", 100.0, price=0.60)]
        new = [_snap("tok1", "YES", 105.0, price=0.60)]  # $3 delta — below threshold
        signals = d._diff_snapshots("0xWHALE", old, new)
        filtered = d._filter_signals(signals)
        assert filtered == []

    def test_large_delta_passes(self):
        """Position change worth >=$100 should pass."""
        d = _detector()
        old = [_snap("tok1", "YES", 100.0, price=0.60)]
        new = [_snap("tok1", "YES", 400.0, price=0.60)]  # $180 delta
        signals = d._diff_snapshots("0xWHALE", old, new)
        filtered = d._filter_signals(signals)
        assert len(filtered) == 1

    def test_delta_neutral_both_sides_filtered(self):
        """If whale holds YES and NO on same market, both should be dropped."""
        d = _detector()
        old = []
        new = [
            _snap("tok-yes", "YES", 300.0, price=0.60, slug="market-x"),
            _snap("tok-no",  "NO",  300.0, price=0.40, slug="market-x"),
        ]
        signals = d._diff_snapshots("0xWHALE", old, new)
        filtered = d._filter_signals(signals)
        assert filtered == []

    def test_delta_neutral_different_markets_not_filtered(self):
        """YES on market-A and NO on market-B should both be kept."""
        d = _detector()
        old = []
        new = [
            _snap("tok1", "YES", 300.0, price=0.60, slug="market-a"),
            _snap("tok2", "NO",  300.0, price=0.40, slug="market-b"),
        ]
        signals = d._diff_snapshots("0xWHALE", old, new)
        filtered = d._filter_signals(signals)
        assert len(filtered) == 2
