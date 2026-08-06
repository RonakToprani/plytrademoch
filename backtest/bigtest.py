"""
backtest/bigtest.py — large-sample, cluster-aware favorite/longshot calibration.

Methodology, and why each part is here:

  • Universe from `resolved_deep` (keyset-paginated, ~10x+ the old 2107-market
    cap). See backtest/universe.py.

  • Ex-ante pricing: each token is priced ONCE at `horizon` hours before its last
    trade, from CLOB price history — never at resolution. Same anchor rule as
    backtest/horizon.py (last timestamp, not nominal end_date, because markets
    routinely stop trading long before their stated end).

  • Both outcome tokens are scored. Scoring only token0 biases the curve, since
    token0 is systematically the underdog side.

  • EVENT CLUSTERING is the point of this module. The live book taught us that 38
    bets were really 13 independent events; treating correlated legs as
    independent observations inflates n and shrinks confidence intervals by
    ~sqrt(legs per event). So:
        - n_events is reported next to n
        - the bootstrap resamples EVENTS with replacement, not rows
    A 45-leg negRisk bucket set contributes one draw, not 45.

  • Segment + time splits: an edge that only exists in one category or one era is
    not an edge you can trade next month.
"""

from __future__ import annotations

import random
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import httpx

_DB = "backtest_cache.db"
_CLOB = "https://clob.polymarket.com/prices-history"


# ---------------------------------------------------------------- price fetch

def _price_at(points: list[tuple[int, float]], horizon_h: int) -> float | None:
    """Last price at or before (last_ts - horizon). None if series too short."""
    if len(points) < 2:
        return None
    target = points[-1][0] - horizon_h * 3600
    if points[0][0] > target:
        return None
    out = None
    for ts, px in points:
        if ts <= target:
            out = px
        else:
            break
    return out


def fetch_horizon_prices(horizons: tuple[int, ...] = (24, 48, 96),
                         workers: int = 12, db_path: str = _DB,
                         limit: int | None = None,
                         min_volume: float = 0.0) -> int:
    """Price every token in resolved_deep at each horizon; cache in horizon_price."""
    db = sqlite3.connect(db_path)
    db.execute("""CREATE TABLE IF NOT EXISTS horizon_price (
                      token_id TEXT NOT NULL, horizon_h INTEGER NOT NULL,
                      price REAL, PRIMARY KEY (token_id, horizon_h))""")
    db.commit()
    done = {r[0] for r in db.execute(
        "SELECT DISTINCT token_id FROM horizon_price WHERE horizon_h=?",
        (horizons[0],))}
    toks: list[str] = []
    for t0, t1 in db.execute(
            "SELECT token0, token1 FROM resolved_deep WHERE volume >= ?",
            (min_volume,)):
        for t in (t0, t1):
            if t and t not in done:
                toks.append(t)
    toks = list(dict.fromkeys(toks))
    if limit:
        toks = toks[:limit]
    print(f"fetching {len(toks)} token histories ({len(done)} already cached)...",
          flush=True)

    def one(tok: str, client: httpx.Client):
        try:
            r = client.get(_CLOB, params={"market": tok, "interval": "max",
                                          "fidelity": 1440})
            r.raise_for_status()
            hist = r.json().get("history", []) or []
            pts = sorted((int(p["t"]), float(p["p"]))
                         for p in hist if "t" in p and "p" in p)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return None
        return tok, [(h, _price_at(pts, h)) for h in horizons]

    wrote, t0 = 0, time.time()
    with httpx.Client(timeout=30.0,
                      limits=httpx.Limits(max_connections=workers)) as client:
        for i in range(0, len(toks), 500):
            chunk = toks[i:i + 500]
            with ThreadPoolExecutor(max_workers=workers) as ex:
                res = [r for r in ex.map(lambda t: one(t, client), chunk) if r]
            db.executemany(
                "INSERT OR REPLACE INTO horizon_price (token_id, horizon_h, price) "
                "VALUES (?,?,?)",
                [(tok, h, p) for tok, hp in res for h, p in hp])
            db.commit()
            wrote += len(res)
            el = time.time() - t0
            print(f"  {i + len(chunk)}/{len(toks)}  ({wrote} ok, "
                  f"{wrote / max(el, 1e-9):.0f}/s)", flush=True)
    db.close()
    return wrote


# ------------------------------------------------------------------ analysis

# Gamma's own `category` is null on virtually every modern market and `tags`
# returns only "All", so segments are derived from the slug. Ordered — first
# match wins, so put the specific patterns before the general ones.
#
# 2026-08-05 recalibration: the old single "sports-game" class hid the split that
# actually matters, and its prefix list missed esports/cricket/UFC entirely (they
# fell through to "other", polluting that segment's +22.5% with game flow). The
# real cut is market STRUCTURE, not sport:
#   game-prop   (draw / exact-score / totals / spread / btts / handicap):
#               +18.2% [+10.7,+25.7] @6h slip 0.01 — still +8.9% EDGE at slip 0.03
#   game-winner (who wins the game/match/series):
#               +7.6% [+2.5,+13.0] @6h slip 0.01 — -0.8% n.s. at slip 0.03
# Winner markets are anchored by sharp sportsbook odds and are efficient once you
# pay the spread; props and score-structure markets have no such anchor and keep
# the favorite-longshot bias. Stable across 6/24/48h horizons.
_SEGMENTS: tuple[tuple[str, str], ...] = (
    ("game-prop",     r"-draw(-|$)|exact-score|-total-\d+pt\d+|"
                      r"-(spread|btts|handicap)(-|$)"),
    ("game-winner",   r"^(nba|nfl|mlb|nhl|ncaab|ncaaf|wnba|epl|ucl|uel|elc|mls|"
                      r"laliga|seriea|bundesliga|ligue1|fifwc|fifa|uefa|copa|lal|"
                      r"atp|wta|tennis|cs2|csgo|lol|dota2?|val|cod|rl|kings|"
                      r"cric\w*|t20\w*|ufc|boxing|mma)-|-vs-|\bvs\.\b"),
    ("sports-season", r"win-the-(20\d\d|202\d\d\d).*(world-cup|champions-league|super-bowl|"
                      r"premier-league|nba-finals|stanley-cup|world-series)|"
                      r"(super-bowl|world-cup|champions-league)-(winner|champion)"),
    ("token-launch",  r"fdv|one-day-after-launch|launch-a-token|market-cap-.*after-launch"),
    ("crypto-price",  r"(bitcoin|ethereum|solana|xrp|dogecoin|btc|eth)-.*"
                      r"(hit|reach|dip|above|below|price|\$?\d{4,})|"
                      r"what-price-will-(bitcoin|ethereum)"),
    ("price-barrier", r"(hit|reach|dip-to|dips-to|above|below)-(high-|low-)?\$?\d|"
                      r"what-price-will|all-time-high|-close-(above|below)"),
    ("election",      r"election|nominee|presidential|mayoral|primary|"
                      r"be-the-next-(president|prime-minister|pope|chair)|win-the-\d{4}"),
    ("geopolitics",   r"ceasefire|invade|blockade|airspace|strike|war|nuclear|"
                      r"troops|capture|annex|sanction|hostage|nato"),
    ("mention-count", r"tweets|mentions|say-|number-of-times|posts-"),
    ("fed-macro",     r"^fed-|fed-(increase|decrease|pause|cut|hike)|interest-rates|"
                      r"recession|cpi|inflation|jobs-report|gdp"),
    ("other",         r"."),
)


def segment_of(slug: str) -> str:
    import re
    for name, pat in _SEGMENTS:
        if re.search(pat, slug or "", re.I):
            return name
    return "other"


@dataclass
class Cell:
    n: int = 0
    wins: int = 0
    roi_sum: float = 0.0
    px_sum: float = 0.0
    events: set = field(default_factory=set)
    # (event, roi) pairs, for the cluster bootstrap
    obs: list = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        return self.wins / self.n if self.n else 0.0

    @property
    def roi(self) -> float:
        return self.roi_sum / self.n if self.n else 0.0

    @property
    def mean_px(self) -> float:
        return self.px_sum / self.n if self.n else 0.0


def _rows(db: sqlite3.Connection, horizon: int, min_volume: float,
          end_min: str | None, end_max: str | None):
    q = ("SELECT d.winning_token_id, d.token0, d.token1, d.event, d.slug, "
         "       d.end_date, h0.price, h1.price "
         "FROM resolved_deep d "
         "LEFT JOIN horizon_price h0 ON h0.token_id=d.token0 AND h0.horizon_h=? "
         "LEFT JOIN horizon_price h1 ON h1.token_id=d.token1 AND h1.horizon_h=? "
         "WHERE d.volume >= ?")
    args: list = [horizon, horizon, min_volume]
    if end_min:
        q += " AND d.end_date >= ?"
        args.append(end_min)
    if end_max:
        q += " AND d.end_date < ?"
        args.append(end_max)
    return db.execute(q, args)


def collect(band_lo: float, band_hi: float, *, horizon: int = 48,
            slippage: float = 0.01, min_volume: float = 30_000.0,
            end_min: str | None = None, end_max: str | None = None,
            by: str = "all", db_path: str = _DB) -> dict[str, Cell]:
    """Gather (event, roi) observations in the band, keyed by segment."""
    db = sqlite3.connect(db_path)
    cells: dict[str, Cell] = {}
    for winner, t0, t1, event, slug, end_date, p0, p1 in _rows(
            db, horizon, min_volume, end_min, end_max):
        for token, price in ((t0, p0), (t1, p1)):
            if not token or price is None:
                continue
            if not (band_lo <= price < band_hi):
                continue
            won = token == winner
            entry = min(0.99, price + slippage)
            roi = (1.0 / entry - 1.0) if won else -1.0
            if by == "segment":
                key = segment_of(slug)
            elif by == "year":
                key = (end_date or "?")[:4]
            else:
                key = "all"
            c = cells.setdefault(key, Cell())
            c.n += 1
            c.wins += int(won)
            c.roi_sum += roi
            c.px_sum += price
            c.events.add(event)
            c.obs.append((event, roi))
    db.close()
    return cells


def bootstrap_ci(obs: list[tuple[str, float]], iters: int = 2000,
                 alpha: float = 0.05, seed: int = 7) -> tuple[float, float]:
    """
    Cluster bootstrap on ROI: resample EVENTS with replacement, keeping each
    event's legs together. Resampling individual legs would understate the
    interval whenever an event contributes many correlated rows.
    """
    if not obs:
        return (0.0, 0.0)
    groups: dict[str, list[float]] = {}
    for ev, roi in obs:
        groups.setdefault(ev, []).append(roi)
    keys = list(groups)
    if len(keys) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        tot = cnt = 0.0
        for _ in range(len(keys)):
            g = groups[keys[rng.randrange(len(keys))]]
            tot += sum(g)
            cnt += len(g)
        means.append(tot / cnt if cnt else 0.0)
    means.sort()
    lo = means[int(alpha / 2 * iters)]
    hi = means[min(iters - 1, int((1 - alpha / 2) * iters))]
    return (lo, hi)


def band_table(horizon: int = 48, slippage: float = 0.01,
               min_volume: float = 30_000.0, db_path: str = _DB) -> None:
    """Favorite/longshot curve across the whole price range, event-clustered."""
    bands = [(0.02, 0.05), (0.05, 0.10), (0.10, 0.15), (0.15, 0.20),
             (0.10, 0.20), (0.20, 0.30), (0.30, 0.40), (0.40, 0.60),
             (0.60, 0.80), (0.80, 0.90), (0.90, 0.98)]
    print(f"\nPRICE-BAND CURVE @ {horizon}h, slippage {slippage}, vol>=${min_volume:,.0f}")
    print(f"  {'band':<12} {'n':>7} {'events':>7} {'win%':>7} {'px':>6} {'ROI':>8}"
          f"  {'95% CI (event-clustered)':>26}")
    print("  " + "-" * 84)
    for lo, hi in bands:
        cells = collect(lo, hi, horizon=horizon, slippage=slippage,
                        min_volume=min_volume, db_path=db_path)
        c = cells.get("all")
        if not c or c.n < 20:
            continue
        cl, ch = bootstrap_ci(c.obs)
        mark = "  <-- strategy band" if (lo, hi) == (0.10, 0.20) else ""
        sig = "EDGE" if cl > 0 else ("neg" if ch < 0 else "n.s.")
        print(f"  {lo:.2f}-{hi:.2f}   {c.n:>7} {len(c.events):>7} {c.win_rate*100:>6.1f}% "
              f"{c.mean_px:>6.3f} {c.roi*100:>+7.1f}%  [{cl*100:>+7.1f}%, {ch*100:>+7.1f}%] "
              f"{sig}{mark}")


def report(cells: dict[str, Cell], title: str, min_n: int = 30) -> None:
    print(f"\n{title}")
    print(f"  {'segment':<22} {'n':>6} {'events':>7} {'win%':>7} {'px':>6} "
          f"{'ROI':>8}  {'95% CI (event-clustered)':>26}")
    print("  " + "-" * 88)
    for key in sorted(cells, key=lambda k: -cells[k].n):
        c = cells[key]
        if c.n < min_n:
            continue
        lo, hi = bootstrap_ci(c.obs)
        sig = "  EDGE" if lo > 0 else ("  neg" if hi < 0 else "  n.s.")
        print(f"  {key[:22]:<22} {c.n:>6} {len(c.events):>7} {c.win_rate*100:>6.1f}% "
              f"{c.mean_px:>6.3f} {c.roi*100:>+7.1f}%  [{lo*100:>+7.1f}%, {hi*100:>+7.1f}%]{sig}")


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(prog="backtest.bigtest")
    sub = p.add_subparsers(dest="cmd", required=True)

    pf = sub.add_parser("fetch", help="price every token at each horizon")
    pf.add_argument("--horizons", type=int, nargs="+", default=[24, 48, 96])
    pf.add_argument("--workers", type=int, default=12)
    pf.add_argument("--min-volume", type=float, default=30_000.0)

    pr = sub.add_parser("report", help="full cluster-aware calibration report")
    pr.add_argument("--horizon", type=int, default=48)
    pr.add_argument("--slippage", type=float, default=0.01)
    pr.add_argument("--min-volume", type=float, default=30_000.0)
    pr.add_argument("--band", type=float, nargs=2, default=[0.10, 0.20])

    a = p.parse_args()
    if a.cmd == "fetch":
        fetch_horizon_prices(tuple(a.horizons), workers=a.workers,
                             min_volume=a.min_volume)
        return

    lo, hi = a.band
    band_table(horizon=a.horizon, slippage=a.slippage, min_volume=a.min_volume)
    for by, title in (("segment", "BY SEGMENT"), ("year", "BY YEAR (stability)")):
        cells = collect(lo, hi, horizon=a.horizon, slippage=a.slippage,
                        min_volume=a.min_volume, by=by)
        report(cells, f"{title} — band {lo:.2f}-{hi:.2f} @ {a.horizon}h")


if __name__ == "__main__":
    main()
