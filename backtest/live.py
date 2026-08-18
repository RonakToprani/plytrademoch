"""
backtest/live.py — Live opportunity scanner for the underdog edge.

Turns the validated backtest finding into an actionable list: which currently-open
markets have a token priced in the underdog band (~0.15–0.33) that the strategy
would buy right now. Read-only; suggests sizes but places nothing.

Strategy (recalibrated 2026-08-05 — see EXPECTATIONS.md):
  • Buy the outcome token priced in [band_lo, band_hi] (default 0.15–0.33; the
    0.30–0.33 slice is +10.7% [+4.5,+17.5] on the gated universe).
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

# Segments with no measured edge in the underdog band, 2026-08-05 recalibration
# (fine-grained classes, event-clustered, ≥$30k volume — see EXPECTATIONS.md):
#
#   game-winner    who-wins markets, ALL sports incl. esports/cricket/tennis/UFC:
#                  +7.6% @6h at slip 0.01, -0.8% n.s. at slip 0.03. Anchored by
#                  sharp sportsbook odds; the edge does not survive the spread.
#                  This was ~85% of the live book's post-fix flow, realized ~flat.
#   mention-count  -3.7%; fed-macro -17.3% — mechanical, publicly-tracked
#                  quantities (tweet counters, fed-funds futures): well calibrated,
#                  no bias to harvest.
#   election       +9.1% n.s. @48h, -8.5% @6h slip 0.03 — poll/model-anchored,
#                  same "external anchor" logic as fed-macro; unproven, not cheap.
#   price-barrier  +0.1% n.s. — barrier-hit markets price off realized vol; dead.
#   token-launch   unstable sign across horizons on n=50-61 events; unmeasurable.
#
# What REMAINS is where the edge is — re-measured 2026-08-17 on the live band
# (0.15-0.33 @48h, slip 0.01, after the classifier leak fixes below):
#   game-prop (draws/exact-score/match totals) +29.4% [+23.9,+34.8] n=4514 ·
#   geopolitics +34.5% [+6.3,+62.2] n=273 · crypto-price +12.4% [+5.7,+18.7]
#   n=2559 · other +12.3% [+5.6,+19.7] n=3025. The gated blend is +20.3%
#   [+16.8,+24.0] and — unlike the old blend — still +10.9% [+7.7,+14.4] EDGE at
#   slip 0.03. Common thread: no external anchor (no sportsbook line, no futures
#   curve, no poll model) → the favorite-longshot bias survives.
#
# 2026-08-17 leak audit: these exclusions are only as good as the regexes in
# `bigtest._SEGMENTS`, and four classes were escaping into the buyable `other`
# bucket — match-shaped slugs from ~30 unlisted leagues (48% of `other`!),
# season/tournament futures, "…-senate-race-in-2026" elections, and ECB/BoJ/
# fed-funds-target decisions. Fixing them RAISED the blend (+18.6% -> +20.3% at
# slip 0.01) and cost zero current flow. See EXPECTATIONS.md; pinned by
# tests/test_segments.py. If you add a segment here, add its slug shapes there.
_NO_EDGE_SEGMENTS = frozenset({
    "game-winner", "mention-count", "fed-macro", "election",
    "price-barrier", "token-launch",
    # Season/tournament futures ("win the 2026 World Series"). Too thin to
    # measure at short horizons, but decisively NEGATIVE whenever they do enter
    # the window: -54.5% [-87.7,-11.0] @168h, -71.2% [-93.1,-46.0] @336h
    # (2026-08-06). The final week of a season future is exactly when it shows
    # up in-window, and that is when it is worst.
    "sports-season",
})

# Per-segment hold-window ceilings (hours), measured 2026-08-06. The blended
# edge decays past 168h (+13.2% @168h -> +10.0% @240h -> +0.8% n.s. @336h), so
# 168h stays the default. Geopolitics is the measured exception — it is the one
# segment still an EDGE at 240h at BOTH slippages (+41.1% [+16.3,+69.3] @0.01,
# +29.5% [+6.9,+55.3] @0.03, n=182 events): war/ceasefire one-offs stay
# mispriced further out. 336h fails the slip-0.03 gate (+20.3% n.s.) and is NOT
# extended to. Capital lock at 10 days is immaterial for this book.
_SEGMENT_MAX_HOURS: dict[str, float] = {
    "geopolitics": 240.0,
}


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
    band_hi: float = 0.33,
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
        segment = segment_of(mk["slug"])
        if segment in exclude_segments:
            continue
        hours = _hours_until(mk.get("end_date"), now)
        seg_max = _SEGMENT_MAX_HOURS.get(segment, max_hours)
        if hours is None or not (min_hours <= hours <= seg_max):
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
# Refit 2026-08-05 on the GATED universe (game-winner/election/price-barrier/
# token-launch now excluded alongside mention-count/fed-macro):
#
#   slice        n     events   win%    mean px   ROI      95% CI
#   0.12-0.15   2048    1780    15.6%   0.133    +9.5%  [-1.4,+20.6] n.s. <- below floor
#   0.15-0.18   2048    1879    21.1%   0.163   +22.2%  [+11.5,+32.5] EDGE
#   0.18-0.21   2013    1854    25.2%   0.193   +24.4%  [+15.0,+33.7] EDGE
#   0.21-0.24   2253    2105    28.9%   0.223   +23.5%  [+15.5,+31.4] EDGE
#   0.24-0.27   2476    2330    30.9%   0.253   +17.5%  [+10.5,+24.4] EDGE
#   0.27-0.30   2460    2310    33.0%   0.282   +12.7%  [+6.6,+19.2] EDGE
#   0.30-0.33   2021    1882    35.8%   0.313   +10.7%  [+4.5,+17.5] EDGE <- in band since 08-05
#   0.33-0.36   1917    1788    36.6%   0.343    +3.7%  [-2.2,+9.9]  n.s. <- dead
#
# The old code used a FLAT 0.245 win rate at every price. That is not a harmless
# simplification — it inverts the sizing. With q fixed, Kelly f = q - (1-q)p/(1-p)
# falls as p rises and turns NEGATIVE above p = 0.245, so the strategy staked most
# at 0.15 (where measured edge is weakest) and refused the top of the band
# entirely. Against the measured curve, full-Kelly runs 0.044 -> 0.080 -> 0.079
# -> 0.066 -> 0.056 across 0.15 -> 0.21 -> 0.24 -> 0.30 -> 0.33, peaking where
# the edge really is.
_WIN_RATE_CURVE: tuple[tuple[float, float], ...] = (
    (0.133, 0.156),
    (0.163, 0.211),
    (0.193, 0.252),
    (0.223, 0.289),
    (0.253, 0.309),
    (0.282, 0.330),
    (0.313, 0.358),
    (0.343, 0.366),   # past the band ceiling; anchors the interpolation at 0.33
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
