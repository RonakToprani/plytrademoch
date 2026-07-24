"""
tests/test_bias.py — Bucketing + horizon-pricing helpers for the calibration tests.

Pure functions, no network.
"""

from __future__ import annotations

from backtest.bias import Bucket, _bucket_edges, _find_bucket
from backtest.horizon import _price_at_horizon


def test_bucket_edges_partition_unit_interval():
    edges = _bucket_edges(0.10)
    assert edges[0] == 0.0 and edges[-1] == 1.0
    assert len(edges) == 11


def test_find_bucket_places_prices():
    buckets = [Bucket(lo, hi) for lo, hi in zip(_bucket_edges(0.10)[:-1], _bucket_edges(0.10)[1:])]
    assert _find_bucket(buckets, 0.05).lo == 0.0
    assert _find_bucket(buckets, 0.55).lo == 0.5
    assert _find_bucket(buckets, 1.0).hi == 1.0          # right edge inclusive at 1.0


def test_bucket_gap_and_winrate():
    b = Bucket(0.7, 0.8)
    b.n, b.win, b.price_sum = 10, 9, 7.4      # mean price 0.74, win rate 0.90
    assert abs(b.mean_price - 0.74) < 1e-9
    assert abs(b.win_rate - 0.90) < 1e-9
    assert abs(b.gap - 0.16) < 1e-9           # favorites underpriced by +16pts


def test_price_at_horizon_picks_point_before_target():
    # points ascending: (ts, price). Last ts = 1000 (anchor).
    points = [(100, 0.30), (600, 0.55), (900, 0.80), (1000, 0.95)]
    # horizon of 400s → target = 600 → last point with ts<=600 is (600, 0.55)
    assert _price_at_horizon(points, 400 / 3600) == 0.55


def test_price_at_horizon_none_when_too_short():
    points = [(900, 0.5), (1000, 0.6)]        # only 100s of history
    assert _price_at_horizon(points, 24) is None    # 24h horizon unreachable
    assert _price_at_horizon([], 1) is None
