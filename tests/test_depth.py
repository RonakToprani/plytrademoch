"""
tests/test_depth.py — Order-book fill math for the depth check. Pure, no network.
"""

from __future__ import annotations

from backtest.depth import analyze


def _book(bids, asks):
    return {"bids": sorted(bids, key=lambda x: x[0], reverse=True),
            "asks": sorted(asks, key=lambda x: x[0])}


def test_best_prices_and_spread():
    fq = analyze(_book([(0.13, 100)], [(0.14, 100), (0.16, 100)]), stake_usd=5)
    assert fq.best_bid == 0.13
    assert fq.best_ask == 0.14
    assert abs(fq.spread - 0.01) < 1e-9
    assert fq.in_band is True


def test_vwap_fill_walks_multiple_levels():
    # $10 stake: $2 at 0.10 (20 sh) + $8 at 0.20 (40 sh) = 60 sh for $10 → VWAP 0.1667
    book = _book([], [(0.10, 20), (0.20, 1000)])
    fq = analyze(book, stake_usd=10.0, band_hi=0.30)
    assert fq.filled_frac == 1.0
    assert abs(fq.avg_fill_price - round(10.0 / 60.0, 4)) < 1e-6


def test_capacity_in_band_sums_only_asks_within_band():
    book = _book([], [(0.15, 100), (0.25, 100)])   # 0.15*100=15 in band; 0.25 out
    fq = analyze(book, stake_usd=1.0, band_hi=0.20)
    assert fq.capacity_in_band == 15.0


def test_thin_book_partial_fill():
    book = _book([], [(0.15, 10)])                 # only $1.50 available
    fq = analyze(book, stake_usd=5.0, band_hi=0.20)
    assert fq.filled_frac < 1.0


def test_empty_or_missing_book():
    assert analyze(None, 5.0).best_ask is None
    assert analyze({"bids": [], "asks": []}, 5.0).filled_frac == 0.0
