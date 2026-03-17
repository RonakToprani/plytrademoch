"""
tests/test_scanner.py — Wallet scoring logic unit tests.

Tests:
  • _composite_score() produces values in [0, 100]
  • filter_wallets() removes wallets below thresholds
  • _passes_thresholds() min-P&L / win-rate / trade-count enforcement
  • Edge cases: 0 trades, negative P&L, zero win rate
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from copy_trading.scanner import WalletScanner
from data.models import TrackedWallet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scanner() -> WalletScanner:
    client = MagicMock()
    db = MagicMock()
    return WalletScanner(client, db)


def _make_wallet(**kwargs) -> TrackedWallet:
    defaults = dict(
        address="0xABCDEF1234567890",
        alias="TestWhale",
        lifetime_pnl=200_000.0,
        win_rate=0.70,
        roi=2.5,
        total_trades=100,
        score=75.0,
        is_active=True,
        last_scanned=datetime.now(timezone.utc),
        estimated_bankroll=500_000.0,
    )
    defaults.update(kwargs)
    return TrackedWallet(**defaults)


# ---------------------------------------------------------------------------
# _composite_score
# ---------------------------------------------------------------------------

class TestCompositeScore:
    def test_score_in_range(self):
        scanner = _make_scanner()
        score = scanner._composite_score(
            lifetime_pnl=200_000,
            win_rate=0.70,
            roi=2.5,
            consistency=0.8,
            recency=1.0,
        )
        assert 0.0 <= score <= 100.0

    def test_perfect_trader_high_score(self):
        scanner = _make_scanner()
        score = scanner._composite_score(
            lifetime_pnl=1_000_000,
            win_rate=1.0,
            roi=10.0,
            consistency=1.0,
            recency=1.0,
        )
        assert score >= 80.0

    def test_zero_everything_gives_zero(self):
        scanner = _make_scanner()
        score = scanner._composite_score(
            lifetime_pnl=0,
            win_rate=0.0,
            roi=0.0,
            consistency=0.0,
            recency=0.0,
        )
        assert score == pytest.approx(0.0)

    def test_higher_pnl_higher_score(self):
        scanner = _make_scanner()
        low = scanner._composite_score(100_000, 0.65, 1.0, 0.5, 1.0)
        high = scanner._composite_score(900_000, 0.65, 1.0, 0.5, 1.0)
        assert high > low

    def test_higher_win_rate_higher_score(self):
        scanner = _make_scanner()
        low = scanner._composite_score(200_000, 0.65, 1.0, 0.5, 1.0)
        high = scanner._composite_score(200_000, 0.95, 1.0, 0.5, 1.0)
        assert high > low

    def test_stale_trader_lower_score(self):
        scanner = _make_scanner()
        recent = scanner._composite_score(200_000, 0.70, 2.5, 0.8, 1.0)
        stale = scanner._composite_score(200_000, 0.70, 2.5, 0.8, 0.0)
        assert recent > stale


# ---------------------------------------------------------------------------
# _passes_thresholds
# ---------------------------------------------------------------------------

class TestPassesThresholds:
    def test_passes_all(self):
        scanner = _make_scanner()
        assert scanner._passes_thresholds(200_000, 0.70, 100) is True

    def test_fails_low_pnl(self):
        scanner = _make_scanner()
        assert scanner._passes_thresholds(50_000, 0.70, 100) is False

    def test_fails_low_win_rate(self):
        scanner = _make_scanner()
        assert scanner._passes_thresholds(200_000, 0.50, 100) is False

    def test_fails_few_trades(self):
        scanner = _make_scanner()
        assert scanner._passes_thresholds(200_000, 0.70, 10) is False

    def test_edge_exact_minimums_pass(self):
        scanner = _make_scanner()
        # Uses settings defaults: min_whale_pnl=100_000, min_win_rate=0.65, min_trades=50
        assert scanner._passes_thresholds(100_000, 0.65, 50) is True


# ---------------------------------------------------------------------------
# filter_wallets
# ---------------------------------------------------------------------------

class TestFilterWallets:
    def test_passes_qualified_wallet(self):
        scanner = _make_scanner()
        result = scanner.filter_wallets([_make_wallet()])
        assert len(result) == 1

    def test_rejects_low_pnl(self):
        scanner = _make_scanner()
        result = scanner.filter_wallets([_make_wallet(lifetime_pnl=50_000)])
        assert len(result) == 0

    def test_rejects_low_win_rate(self):
        scanner = _make_scanner()
        result = scanner.filter_wallets([_make_wallet(win_rate=0.50)])
        assert len(result) == 0

    def test_rejects_too_few_trades(self):
        scanner = _make_scanner()
        result = scanner.filter_wallets([_make_wallet(total_trades=10)])
        assert len(result) == 0

    def test_mixed_list(self):
        scanner = _make_scanner()
        wallets = [
            _make_wallet(address="0x1"),
            _make_wallet(address="0x2", lifetime_pnl=1_000),
            _make_wallet(address="0x3", win_rate=0.40),
            _make_wallet(address="0x4"),
        ]
        result = scanner.filter_wallets(wallets)
        assert len(result) == 2
        addresses = {w.address for w in result}
        assert addresses == {"0x1", "0x4"}

    def test_empty_list(self):
        scanner = _make_scanner()
        result = scanner.filter_wallets([])
        assert result == []
