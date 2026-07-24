"""
backtest/edge.py — Score copy entries against resolution ground truth.

The test models what a copy bot actually experiences:

  A whale BUYs an outcome token at price ``p``. We see it seconds later and copy
  it, but we cross the spread and the whale's own buy has already moved the
  price, so our effective entry is ``p + slippage``. We can't match the whale's
  exit timing, so we hold to resolution. The market settles to $1 (won) or $0
  (lost).

  Return on $1 staked = (1/entry_eff) - 1   if the outcome won
                      = -1                    if it lost

Averaging that return across many independent resolved entries tells us whether
following the whale has real edge *after costs*. A bootstrap CI says whether the
edge is distinguishable from zero, and a slippage sweep says how much execution
cost the edge can survive — the number that actually decides go / no-go.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from backtest.datafeed import DataFeed, Trade


@dataclass(frozen=True)
class Entry:
    """A single copyable entry derived from a whale BUY."""

    ts: int
    condition_id: str
    asset: str            # token id the whale bought — matched against the winner
    outcome_index: int
    price: float
    usdc_size: float
    slug: str


@dataclass
class ScoredResult:
    slippage: float
    n_entries: int          # entries on resolved markets, in price band
    n_wins: int
    win_rate: float
    mean_roi: float         # equal-weighted return per $1 staked
    roi_ci: tuple[float, float]
    notional_roi: float     # dollar-weighted (size the whale actually bet)
    avg_entry_price: float
    total_signals: int      # BUYs seen before resolution/band filtering
    n_resolved: int         # of those, how many on resolved markets


def build_entries(trades: list[Trade], side: str = "BUY") -> list[Entry]:
    """Derive copyable entries from a wallet's activity (each BUY = one entry)."""
    return [
        Entry(
            ts=t.ts,
            condition_id=t.condition_id,
            asset=t.asset,
            outcome_index=t.outcome_index,
            price=t.price,
            usdc_size=t.usdc_size,
            slug=t.slug,
        )
        for t in trades
        if t.side == side and t.condition_id and t.asset and 0.0 < t.price < 1.0
    ]


def score(
    entries: list[Entry],
    feed: DataFeed,
    *,
    slippage: float = 0.01,
    min_price: float = 0.08,
    max_price: float = 0.92,
    min_hold_seconds: int = 0,
    bootstrap_iters: int = 2_000,
) -> ScoredResult:
    """
    Score *entries* against resolution ground truth with a fixed slippage cost.

    Filters (mirroring the live executor's math guards):
      • market must be resolved with a known winning outcome
      • whale entry price within [min_price, max_price]
    """
    resolved_cache: dict[str, str | None] = {}

    def winning_token(cond: str) -> str | None:
        if cond not in resolved_cache:
            res = feed.get_resolution(cond)
            resolved_cache[cond] = res.winning_token_id if (res and res.closed) else None
        return resolved_cache[cond]

    rois: list[float] = []
    notional_pnl = 0.0
    notional_stake = 0.0
    wins = 0
    entry_price_sum = 0.0
    n_resolved = 0

    for e in entries:
        if not (min_price <= e.price <= max_price):
            continue
        win_token = winning_token(e.condition_id)
        if win_token is None:
            continue
        n_resolved += 1

        entry_eff = min(0.99, e.price + slippage)
        won = e.asset == win_token
        roi = (1.0 / entry_eff - 1.0) if won else -1.0

        rois.append(roi)
        wins += int(won)
        entry_price_sum += e.price
        stake = e.usdc_size if e.usdc_size > 0 else 1.0
        notional_stake += stake
        notional_pnl += roi * stake

    n = len(rois)
    mean_roi = sum(rois) / n if n else 0.0
    ci = _bootstrap_mean_ci(rois, bootstrap_iters) if n >= 5 else (0.0, 0.0)

    return ScoredResult(
        slippage=slippage,
        n_entries=n,
        n_wins=wins,
        win_rate=wins / n if n else 0.0,
        mean_roi=mean_roi,
        roi_ci=ci,
        notional_roi=(notional_pnl / notional_stake) if notional_stake else 0.0,
        avg_entry_price=entry_price_sum / n if n else 0.0,
        total_signals=len(entries),
        n_resolved=n_resolved,
    )


def slippage_sweep(
    entries: list[Entry],
    feed: DataFeed,
    slippages: tuple[float, ...] = (0.0, 0.005, 0.01, 0.02, 0.03, 0.05),
    **kwargs,
) -> list[ScoredResult]:
    """Score the same entries across a range of slippage assumptions."""
    return [score(entries, feed, slippage=s, **kwargs) for s in slippages]


def _bootstrap_mean_ci(
    values: list[float], iters: int, alpha: float = 0.05
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean of *values*."""
    if not values:
        return (0.0, 0.0)
    n = len(values)
    means = []
    for _ in range(iters):
        sample = [values[random.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((alpha / 2) * iters)]
    hi = means[int((1 - alpha / 2) * iters) - 1]
    return (lo, hi)
