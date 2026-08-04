"""
backtest/live.py — Live opportunity scanner for the underdog edge.

Turns the validated backtest finding into an actionable list: which currently-open
markets have a token priced in the underdog band (~0.15–0.30) that the strategy
would buy right now. Read-only; suggests sizes but places nothing.

Strategy (from FINDINGS.md §2, validated across horizons + time split):
  • Buy the outcome token priced in [band_lo, band_hi] (default 0.15–0.30).
  • Resolution window: every horizon from 6h to 168h is significantly positive
    (+14.7% at 6h, +16.5% at 24h, +15.6% at 96h, +12.5% at 168h), so the window is
    set for FLOW: [min_hours, max_hours] default 6h–168h. It still excludes
    far-dated, highly correlated markets (e.g. 2028-election longshots 2 years
    out), which lock capital for years.
  • Only liquid markets (volume >= min_volume).
  • Skip segments with no measured edge (see _NO_EDGE_SEGMENTS).
  • One bet per event (avoid correlated mutually-exclusive legs).
  • Hold to resolution.

Sizing: fractional Kelly against `calibrated_win_rate(price)` — the empirically
measured P(win) at that price, not a flat band average. See the curve below;
using a constant inverts the sizing. Negative skew means small, diversified stakes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backtest.bigtest import segment_of
from backtest.datafeed import DataFeed

# Segments with no measured edge in the underdog band. Both are markets on a
# MECHANICAL, publicly-tracked quantity — a running tweet count, a rate decision
# priced off fed-funds futures — so the "distribution" is already well calibrated
# and there is no favourite-longshot bias to harvest. Measured at 0.15-0.30, 48h,
# event-clustered: mention-count -3.7% (n=634/264ev), fed-macro -17.3% (n=43/30ev),
# and mention-count is negative at EVERY horizon (24h -1%, 48h -4%, 96h -5%) and in
# both 2024 (-19%) and 2025 (-6%). Dropping the two lifts band ROI +16.7% -> +17.9%.
#
# This is not a fishing expedition over segment labels: these were the two the live
# book was most concentrated in (6 Elon tweet-count buckets, 4 legs of one Fed
# decision) and the two EXPECTATIONS.md already flagged as unproven.
_NO_EDGE_SEGMENTS = frozenset({"mention-count", "fed-macro"})


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
    segment: str
    est_win_rate: float
    kelly_fraction: float
    suggested_stake: float


def scan(
    feed: DataFeed,
    *,
    band_lo: float = 0.15,
    band_hi: float = 0.30,
    min_hours: float = 6.0,
    max_hours: float = 168.0,
    min_volume: float = 30_000.0,
    bankroll: float = 100.0,
    kelly_multiple: float = 0.25,
    max_stake_frac: float = 0.05,
    min_stake: float = 1.0,
    exclude_segments: frozenset[str] = _NO_EDGE_SEGMENTS,
) -> list[Opportunity]:
    """Return current underdog opportunities, one per event, best-diversified first."""
    now = datetime.now(timezone.utc)
    markets = feed.fetch_open_markets(min_volume=min_volume)

    best_by_event: dict[str, Opportunity] = {}
    for mk in markets:
        hours = _hours_until(mk.get("end_date"), now)
        if hours is None or not (min_hours <= hours <= max_hours):
            continue
        segment = segment_of(mk["slug"])
        if segment in exclude_segments:
            continue
        for token_price, outcome, token in zip(mk["prices"], mk["outcomes"], mk["tokens"]):
            if not (band_lo <= token_price <= band_hi):
                continue
            q = calibrated_win_rate(token_price)
            f = _kelly_fraction(token_price, q) * kelly_multiple
            if f <= 0:
                continue
            # Kelly says how much this bet is worth; if that is under the minimum
            # ticket, the honest answer is "don't", not "round it up to $1". Rounding
            # up inverted the whole point of sizing — the least-attractive prices got
            # the same ticket as the best ones.
            stake = min(f * bankroll, max_stake_frac * bankroll)
            if stake < min_stake:
                continue
            opp = Opportunity(
                condition_id=mk["condition_id"], slug=mk["slug"], event=mk["event"],
                question=mk["question"],
                outcome=outcome, token=token, price=token_price, hours_to_resolve=hours,
                volume=mk["volume"], segment=segment, est_win_rate=round(q, 4),
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


# Measured (mean price -> realised win rate) inside the band, 48h horizon,
# volume >= $30k, no-edge segments excluded, event-clustered. These are the
# empirical calibration curve: what fraction of tokens priced HERE actually win.
#
#   slice        n     events   win%    mean px   ROI      95% CI
#   0.12-0.15   2590    2264    14.6%   0.133    +2.3%  [-7.5,+11.5] n.s. <- below floor
#   0.15-0.18   2655    2424    20.0%   0.163   +15.5%  [+7.4,+24.1] EDGE
#   0.18-0.21   2766    2539    24.6%   0.193   +21.3%  [+12.9,+29.4] EDGE
#   0.21-0.24   3087    2835    27.8%   0.223   +19.0%  [+11.9,+26.1] EDGE
#   0.24-0.27   3391    3128    29.7%   0.253   +12.9%  [+7.3,+19.2] EDGE
#   0.27-0.30   3508    3242    32.6%   0.283   +11.2%  [+6.3,+16.7] EDGE
#   0.30-0.33   3226    2969    35.0%   0.313    +8.2%  [+2.8,+13.0] EDGE <- thin
#   0.33-0.36   3196    2953    36.2%   0.343    +2.5%  [-2.3,+6.9]  n.s. <- dead
#
# The old code used a FLAT 0.245 win rate at every price. That is not a harmless
# simplification — it inverts the sizing. With q fixed, Kelly f = q - (1-q)p/(1-p)
# falls as p rises and turns NEGATIVE above p = 0.245, so the strategy staked most
# at 0.15 (where measured edge is weakest, +15.5%) and refused to trade 0.245-0.25
# at all. Against the measured curve, full-Kelly instead runs 0.044 -> 0.066 ->
# 0.071 -> 0.059 across those slices, peaking near 0.22 where the edge really is.
_WIN_RATE_CURVE: tuple[tuple[float, float], ...] = (
    (0.133, 0.146),
    (0.163, 0.200),
    (0.193, 0.246),
    (0.223, 0.278),
    (0.253, 0.297),
    (0.283, 0.326),
    (0.313, 0.350),   # past the band ceiling; anchors the interpolation at 0.30
)


def calibrated_win_rate(price: float) -> float:
    """
    Empirical P(win | token priced here), linearly interpolated between measured
    anchors and clamped at the ends. Sizing input only — the go/no-go is still
    price-in-band. Beyond the last anchor we hold the last observed q/p ratio
    rather than extrapolating a trend we have not measured.
    """
    pts = _WIN_RATE_CURVE
    if price <= pts[0][0]:
        return pts[0][1] * (price / pts[0][0])
    if price >= pts[-1][0]:
        return min(0.99, pts[-1][1] * (price / pts[-1][0]))
    for (p0, q0), (p1, q1) in zip(pts, pts[1:]):
        if p0 <= price <= p1:
            w = (price - p0) / (p1 - p0)
            return q0 + w * (q1 - q0)
    return pts[-1][1]


def _kelly_fraction(price: float, win_rate: float) -> float:
    """
    Kelly fraction for buying a binary token at `price` with true prob `win_rate`.
    Net odds b = (1-price)/price; f* = (b*q - (1-q)) / b = q - (1-q)*price/(1-price).
    """
    if not (0 < price < 1):
        return 0.0
    q = win_rate
    return q - (1 - q) * price / (1 - price)
