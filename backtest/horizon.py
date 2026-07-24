"""
backtest/horizon.py — Honest favorite/longshot calibration at a fixed lead time.

This fixes the timing bias in `bias.py`. Instead of pooling fills that cluster
near resolution (where price has already converged), we price each market ONCE,
at a fixed horizon before it stopped trading, using the CLOB price history:

    anchor  = last timestamp in the token's price series (≈ resolution)
    p       = the token's price at (anchor - horizon_hours)
    outcome = did that token resolve to $1?

Bucketing (p, outcome) across many markets gives a genuine ex-ante calibration
curve: "H hours before resolution, at price p, how often did it actually win?"
That is the number that decides whether buying favorites (or fading longshots)
is a real edge after slippage — not hindsight.

One data point per market (the first outcome token), so the sample size is the
market count, not the fill count. Neutral universe, no whale selection.
"""

from __future__ import annotations

from dataclasses import dataclass

from backtest.bias import Bucket, _bucket_edges, _find_bucket
from backtest.datafeed import DataFeed, ResolvedMarket


@dataclass
class HorizonResult:
    horizon_hours: int
    slippage: float
    buckets: list[Bucket]
    n_markets: int      # markets with a usable price at this horizon
    n_skipped: int      # markets too short-lived or missing history


def calibrate_at_horizon(
    feed: DataFeed,
    universe: list[ResolvedMarket],
    *,
    horizon_hours: int = 48,
    slippage: float = 0.01,
    bucket_width: float = 0.10,
    min_price: float = 0.02,
    max_price: float = 0.98,
    fidelity: int = 1440,
    progress: bool = False,
) -> HorizonResult:
    """Price each market at `horizon_hours` before its last trade, then bucket."""
    edges = _bucket_edges(bucket_width)
    buckets = [Bucket(lo, hi) for lo, hi in zip(edges[:-1], edges[1:])]

    n_markets = 0
    n_skipped = 0
    for i, mk in enumerate(universe):
        if not mk.sample_token or mk.winning_token_id is None:
            n_skipped += 1
            continue
        points = feed.fetch_price_history(mk.sample_token, fidelity=fidelity)
        price = _price_at_horizon(points, horizon_hours)
        if price is None or not (min_price <= price <= max_price):
            n_skipped += 1
            continue

        won = mk.sample_token == mk.winning_token_id
        entry_eff = min(0.99, price + slippage)
        roi = (1.0 / entry_eff - 1.0) if won else -1.0

        b = _find_bucket(buckets, price)
        if b is None:
            n_skipped += 1
            continue
        b.n += 1
        b.win += int(won)
        b.price_sum += price
        b.roi_sum += roi
        b._rois.append(roi)
        n_markets += 1
        if progress and (i + 1) % 100 == 0:
            print(f"  ...{i + 1}/{len(universe)} markets, {n_markets} usable", flush=True)

    return HorizonResult(horizon_hours=horizon_hours, slippage=slippage,
                         buckets=buckets, n_markets=n_markets, n_skipped=n_skipped)


def _price_at_horizon(points: list[tuple[int, float]], horizon_hours: int) -> float | None:
    """
    Price at (last_ts - horizon_hours). Returns None if the series doesn't reach
    back that far (market younger than the horizon) or is empty.
    """
    if len(points) < 2:
        return None
    anchor = points[-1][0]
    target = anchor - horizon_hours * 3600
    if points[0][0] > target:
        return None  # market didn't exist yet at this horizon
    price = None
    for ts, px in points:
        if ts <= target:
            price = px
        else:
            break
    return price
