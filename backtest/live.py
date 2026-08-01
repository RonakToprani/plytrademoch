"""
backtest/live.py — Live opportunity scanner for the underdog edge.

Turns the validated backtest finding into an actionable list: which currently-open
markets have a token priced in the underdog band (~0.15–0.25) that the strategy
would buy right now. Read-only; suggests sizes but places nothing.

Strategy (from FINDINGS.md §2, validated across horizons + time split):
  • Buy the outcome token priced in [band_lo, band_hi] (default 0.15–0.25).
  • Resolution window: ROI is flat from 6h to 120h (+16.6% at 6h, +19.3% at 36h,
    +16.5% at 96h, +15.3% at 120h) and only falls off at 168h (+13.0%), so the
    window is set for FLOW: [min_hours, max_hours] default 6h–96h. It still
    excludes far-dated, highly correlated markets (e.g. 2028-election longshots
    2 years out), which lock capital for years.
  • Only liquid markets (volume >= min_volume).
  • One bet per event (avoid correlated mutually-exclusive legs).
  • Hold to resolution.

Sizing: fractional Kelly using the band's empirically-calibrated win rate
(0.245 in 0.15-0.25), which is where the edge comes from — NOT the market price.
Negative skew means small, well-diversified stakes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backtest.datafeed import DataFeed

# Empirically-calibrated win rate inside the underdog band (backtest §2).
# Used ONLY for sizing; the go/no-go is price-in-band.
_BAND_WIN_RATE = 0.245


@dataclass
class Opportunity:
    condition_id: str
    slug: str
    event: str
    question: str
    outcome: str
    token: str
    price: float
    hours_to_resolve: float
    volume: float
    est_win_rate: float
    kelly_fraction: float
    suggested_stake: float


def scan(
    feed: DataFeed,
    *,
    band_lo: float = 0.15,
    band_hi: float = 0.25,
    min_hours: float = 6.0,
    max_hours: float = 96.0,
    min_volume: float = 30_000.0,
    bankroll: float = 100.0,
    kelly_multiple: float = 0.25,
    max_stake_frac: float = 0.05,
    min_stake: float = 1.0,
) -> list[Opportunity]:
    """Return current underdog opportunities, one per event, best-diversified first."""
    now = datetime.now(timezone.utc)
    markets = feed.fetch_open_markets(min_volume=min_volume)

    best_by_event: dict[str, Opportunity] = {}
    for mk in markets:
        hours = _hours_until(mk.get("end_date"), now)
        if hours is None or not (min_hours <= hours <= max_hours):
            continue
        for token_price, outcome, token in zip(mk["prices"], mk["outcomes"], mk["tokens"]):
            if not (band_lo <= token_price <= band_hi):
                continue
            f = _kelly_fraction(token_price, _BAND_WIN_RATE) * kelly_multiple
            if f <= 0:
                continue
            stake = min(f * bankroll, max_stake_frac * bankroll)
            if stake < min_stake:
                stake = min_stake
            opp = Opportunity(
                condition_id=mk["condition_id"], slug=mk["slug"], event=mk["event"],
                question=mk["question"],
                outcome=outcome, token=token, price=token_price, hours_to_resolve=hours,
                volume=mk["volume"], est_win_rate=_BAND_WIN_RATE,
                kelly_fraction=round(f, 4), suggested_stake=round(stake, 2),
            )
            # one bet per event — keep the higher-volume (more liquid) leg
            key = mk["event"] or mk["slug"]
            if key not in best_by_event or opp.volume > best_by_event[key].volume:
                best_by_event[key] = opp

    return sorted(best_by_event.values(), key=lambda o: o.volume, reverse=True)


def _hours_until(end_date: str | None, now: datetime) -> float | None:
    if not end_date:
        return None
    try:
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return (end - now).total_seconds() / 3600.0


def _kelly_fraction(price: float, win_rate: float) -> float:
    """
    Kelly fraction for buying a binary token at `price` with true prob `win_rate`.
    Net odds b = (1-price)/price; f* = (b*q - (1-q)) / b = q - (1-q)*price/(1-price).
    """
    if not (0 < price < 1):
        return 0.0
    q = win_rate
    return q - (1 - q) * price / (1 - price)
