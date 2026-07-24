"""
backtest/bias.py — Favorite / longshot bias: is the market's price calibrated?

For a large, neutral set of resolved binary markets we pool *all* BUY-taker
fills (every trader, both outcomes) and ask, per price bucket:

    at price p, what fraction of those tokens actually resolved to $1?

If the market is well calibrated, the realized win rate in the p-bucket equals p
and there is no edge. Systematic deviations are the classic favorite/longshot
bias — longshots (low p) overpriced, favorites (high p) underpriced — and are
tradeable if the gap survives our slippage + the losing side's carry.

For each bucket we report:
  • realized win rate vs mean price (the calibration gap)
  • ROI of BUYING that bucket's token, at a given slippage (hold to resolution)

Prices come from Data API /trades (neutral counterparties); resolution from the
Gamma closed-markets listing. Nothing here is whale-selected.

⚠️  TIMING BIAS — read before trusting these numbers.
    /trades returns a market's MOST RECENT fills, which cluster just before
    resolution, when the price has already converged toward the outcome. That
    over-credits favorites: a token trading at 0.75 the day before it resolves
    really does win ~90%+, but that is hindsight, not an ex-ante edge you could
    have captured. Expect this method to OVERSTATE the favorite edge badly
    (published Polymarket favorite-longshot edge is ~2-5%/contract, not +20%).
    The honest measurement prices each market at a FIXED lead time before
    resolution — see `horizon.py` / the `horizon` CLI. Treat this module as a
    fast, biased first look only.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from backtest.datafeed import DataFeed, ResolvedMarket


@dataclass
class Bucket:
    lo: float
    hi: float
    n: int = 0
    win: int = 0
    price_sum: float = 0.0
    roi_sum: float = 0.0            # sum of per-print ROI of buying at (price+slip)
    _rois: list[float] = field(default_factory=list)

    @property
    def mean_price(self) -> float:
        return self.price_sum / self.n if self.n else 0.0

    @property
    def win_rate(self) -> float:
        return self.win / self.n if self.n else 0.0

    @property
    def gap(self) -> float:
        """Realized win rate minus mean price. >0 → underpriced, <0 → overpriced."""
        return self.win_rate - self.mean_price

    @property
    def mean_roi(self) -> float:
        return self.roi_sum / self.n if self.n else 0.0

    def roi_ci(self, iters: int = 2_000, alpha: float = 0.05) -> tuple[float, float]:
        """Percentile bootstrap CI for this bucket's mean buy-ROI."""
        vals = self._rois
        if len(vals) < 5:
            return (float("-inf"), float("inf"))
        n = len(vals)
        means = sorted(
            sum(vals[random.randrange(n)] for _ in range(n)) / n
            for _ in range(iters)
        )
        return (means[int((alpha / 2) * iters)], means[int((1 - alpha / 2) * iters) - 1])


@dataclass
class CalibrationResult:
    slippage: float
    buckets: list[Bucket]
    n_markets: int
    n_prints: int


def calibrate(
    feed: DataFeed,
    universe: list[ResolvedMarket],
    *,
    slippage: float = 0.01,
    bucket_width: float = 0.10,
    trades_per_market: int = 500,
    min_price: float = 0.02,
    max_price: float = 0.98,
    progress: bool = False,
) -> CalibrationResult:
    """Pool neutral BUY prints across *universe* and bucket them by price."""
    edges = _bucket_edges(bucket_width)
    buckets = [Bucket(lo, hi) for lo, hi in zip(edges[:-1], edges[1:])]

    n_prints = 0
    n_markets = 0
    for i, mk in enumerate(universe):
        if mk.winning_token_id is None:
            continue
        prints = feed.fetch_market_trades(mk.condition_id, max_rows=trades_per_market)
        if not prints:
            continue
        n_markets += 1
        for pr in prints:
            if not (min_price <= pr.price <= max_price):
                continue
            b = _find_bucket(buckets, pr.price)
            if b is None:
                continue
            won = pr.asset == mk.winning_token_id
            entry_eff = min(0.99, pr.price + slippage)
            roi = (1.0 / entry_eff - 1.0) if won else -1.0
            b.n += 1
            b.win += int(won)
            b.price_sum += pr.price
            b.roi_sum += roi
            b._rois.append(roi)
            n_prints += 1
        if progress and (i + 1) % 50 == 0:
            print(f"  ...{i + 1}/{len(universe)} markets, {n_prints} prints", flush=True)

    return CalibrationResult(slippage=slippage, buckets=buckets,
                             n_markets=n_markets, n_prints=n_prints)


def _bucket_edges(width: float) -> list[float]:
    edges = [0.0]
    x = width
    while x < 1.0 - 1e-9:
        edges.append(round(x, 4))
        x += width
    edges.append(1.0)
    return edges


def _find_bucket(buckets: list[Bucket], price: float) -> Bucket | None:
    for b in buckets:
        if b.lo <= price < b.hi or (b.hi == 1.0 and price == 1.0):
            return b
    return None
