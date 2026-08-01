"""
paper/review.py — Nightly strategy review + recommendations.

Runs every evening (launchd). Three things:
  1. Grades the paper book against the backtest expectation (ROI vs ~+17%,
     win rate vs ~24.5%) and breaks results down by entry-price and outcome side.
  2. Re-checks the edge on the cached resolved-market universe across a range of
     price bands — is 0.10–0.20 still the sweet spot, is it decaying, is an
     adjacent band better? (fast: all from cache, no network.)
  3. Emits concrete, rule-based recommendations + adjacent strategies to test.

Writes a dated markdown report to reports/ and sends a Telegram summary. Read-only
analysis — changes nothing on its own.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from backtest.datafeed import DataFeed
from backtest.horizon import _price_at_horizon
from paper.notify import PaperNotifier
from paper.store import PaperStore
from utils.logger import get_logger

logger = get_logger(__name__)

_REPORT_DIR = "reports"
# Bands to scan for edge (both tokens, cached prices). Current live band is 0.15–0.25.
_LIVE_BAND = (0.15, 0.25)   # keep in sync with PaperTrader band_lo/band_hi
_BANDS = [(0.02, 0.10), (0.10, 0.15), (0.15, 0.20), (0.15, 0.25),
          (0.20, 0.30), (0.30, 0.40), (0.80, 0.90), (0.90, 0.98)]


def _band_calibration(feed: DataFeed, horizon_hours: int = 48) -> dict[tuple, dict]:
    """
    Both-token win rate + buy-ROI per price band.

    Reads the deep universe (resolved_deep + horizon_price, ~356k markets / 219k
    events) rather than the old 2107-market cache. The small cache produced
    wildly overstated per-band numbers — it reported 0.10-0.15 at +56% ROI on
    n=64 when the large sample puts it at +5.9% and NOT significant, so the
    nightly recommendation was pointing the opposite way to the evidence.

    Falls back to the legacy cached path if the deep tables aren't built yet.
    """
    try:
        from backtest.bigtest import collect
        out: dict[tuple, dict] = {}
        for lo, hi in _BANDS:
            c = collect(lo, hi, horizon=horizon_hours, min_volume=30_000.0).get("all")
            out[(lo, hi)] = {
                "n": c.n if c else 0,
                "events": len(c.events) if c else 0,
                "win_rate": c.win_rate if c else 0.0,
                "mean_price": c.mean_px if c else 0.0,
                "buy_roi": c.roi if c else 0.0,
            }
        if any(v["n"] for v in out.values()):
            return out
    except (ImportError, Exception):  # noqa: B014 - fall back to the legacy path
        pass
    return _band_calibration_legacy(feed, horizon_hours)


def _band_calibration_legacy(feed: DataFeed, horizon_hours: int = 48) -> dict[tuple, dict]:
    """Both-token win rate + buy-ROI per price band, from cached data only."""
    universe = feed.fetch_resolved_universe(max_markets=5000)   # cached
    acc = {b: {"n": 0, "win": 0, "psum": 0.0, "roi": 0.0} for b in _BANDS}
    for mk in universe:
        if mk.winning_token_id is None:
            continue
        for tok in (mk.sample_token, mk.token1):
            if not tok:
                continue
            pts = feed.fetch_price_history(tok)                 # cached
            p = _price_at_horizon(pts, horizon_hours)
            if p is None:
                continue
            won = tok == mk.winning_token_id
            entry_eff = min(0.99, p + 0.01)
            roi = (1.0 / entry_eff - 1.0) if won else -1.0
            for lo, hi in _BANDS:
                if lo <= p < hi:
                    a = acc[(lo, hi)]
                    a["n"] += 1
                    a["win"] += int(won)
                    a["psum"] += p
                    a["roi"] += roi
    out = {}
    for b, a in acc.items():
        n = a["n"]
        out[b] = {
            "n": n,
            "win_rate": (a["win"] / n) if n else 0.0,
            "mean_price": (a["psum"] / n) if n else 0.0,
            "buy_roi": (a["roi"] / n) if n else 0.0,
        }
    return out


def _paper_breakdown(store: PaperStore) -> dict:
    """Break settled paper bets down by entry-price bucket."""
    settled = [b for b in store.all_bets(limit=5000) if b.status in ("WON", "LOST")]
    # Buckets span the pre-change band too, so bets opened under 0.10–0.20 still
    # land somewhere sensible while the book turns over.
    buckets: dict[str, list] = {"<0.15": [], "0.15–0.20": [], "0.20–0.25": []}
    for b in settled:
        key = ("<0.15" if b.entry_price < 0.15 else
               "0.15–0.20" if b.entry_price < 0.20 else "0.20–0.25")
        buckets[key].append(b)
    rows = {}
    for k, bs in buckets.items():
        n = len(bs)
        if n:
            wins = sum(1 for b in bs if b.status == "WON")
            pnl = sum(b.pnl or 0 for b in bs)
            stake = sum(b.stake_usd for b in bs)
            rows[k] = {"n": n, "win_rate": wins / n, "pnl": pnl,
                       "roi": (pnl / stake) if stake else 0.0}
    return rows


def _recommendations(stats: dict, cal: dict, breakdown: dict) -> list[str]:
    recs: list[str] = []
    settled = stats["settled"]

    if settled < 15:
        recs.append(f"SAMPLE: only {settled} settled bets — too few to act on yet. "
                    "Keep the current 0.15–0.25 / 6–72h config running; revisit at 30+.")
    else:
        roi, wr = stats["roi"], stats["win_rate"]
        if roi >= 0.17:
            recs.append(f"ON TRACK: realized ROI {roi*100:+.0f}% is at/above the backtest "
                        "expectation (~+17%) — no change needed.")
        elif roi >= 0:
            recs.append(f"MARGINAL: realized ROI {roi*100:+.0f}% is positive but below the "
                        "~+17% backtest expectation — could be variance (negative skew) "
                        "or slippage; keep running, watch win rate.")
        else:
            recs.append(f"UNDERPERFORMING: realized ROI {roi*100:+.0f}% vs ~+17% expected. "
                        "Check the band table below — if the 0.15–0.25 edge has decayed, tighten.")
        if wr < 0.15 and settled >= 20:
            recs.append(f"WIN RATE low ({wr*100:.0f}% vs ~24.5%) — either variance or fills are "
                        "landing too high in the band; consider capping entry at 0.17.")

    # Which live sub-band looks best out-of-sample right now. Compare against
    # _LIVE_BAND rather than a hardcoded pair — the live band moved to 0.15-0.25
    # and hardcoding (0.10, 0.20) made this KeyError once it left _BANDS.
    subbands = {b: cal[b] for b in [(0.10, 0.15), (0.15, 0.20)]
                if b in cal and cal[b]["n"] >= 20}
    live = cal.get(_LIVE_BAND)
    if subbands and live:
        best = max(subbands, key=lambda b: subbands[b]["buy_roi"])
        bd = cal[best]
        recs.append(f"BAND: {best[0]:.2f}–{best[1]:.2f} leads out-of-sample "
                    f"(win {bd['win_rate']*100:.0f}%, ROI {bd['buy_roi']*100:+.0f}%, n={bd['n']}). "
                    + ("Consider narrowing the live band to it."
                       if best != _LIVE_BAND and bd["buy_roi"] > live["buy_roi"] + 0.05
                       else f"Current {_LIVE_BAND[0]:.2f}–{_LIVE_BAND[1]:.2f} band "
                            "remains well-placed."))

    # Adjacent-strategy signals
    c2 = cal[(0.20, 0.30)]
    if c2["n"] >= 20 and c2["buy_roi"] > 0.10:
        recs.append(f"ADJACENT: the 0.20–0.30 band also shows edge (ROI {c2['buy_roi']*100:+.0f}%, "
                    f"n={c2['n']}) — worth testing widening the band to 0.15–0.30 for more flow.")
    fav = cal[(0.80, 0.90)]
    if fav["n"] >= 20 and fav["buy_roi"] < -0.05:
        recs.append(f"ADJACENT: strong favorites (0.80–0.90) buy-ROI {fav['buy_roi']*100:+.0f}% "
                    "confirms they're overpriced — a 'fade-the-favorite' (buy the underdog side) "
                    "variant is the same edge from the other end; already captured.")
    low = cal[(0.02, 0.10)]
    if low["n"] >= 20:
        verdict = "also underpriced" if low["buy_roi"] > 0.10 else "NOT an edge (efficient/negative)"
        recs.append(f"ADJACENT: deep longshots (<0.10) are {verdict} "
                    f"(ROI {low['buy_roi']*100:+.0f}%, n={low['n']}) — "
                    + ("could extend the band down." if low["buy_roi"] > 0.10
                       else "keep the 0.15 floor."))

    if breakdown:
        worst = min(breakdown, key=lambda k: breakdown[k]["roi"])
        if breakdown[worst]["n"] >= 8 and breakdown[worst]["roi"] < -0.3:
            recs.append(f"PAPER: your {worst} entry bucket is the weakest so far "
                        f"(ROI {breakdown[worst]['roi']*100:+.0f}%, n={breakdown[worst]['n']}).")
    return recs


def run_review(send: bool = True) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store = PaperStore()
    stats = store.stats()
    breakdown = _paper_breakdown(store)
    with DataFeed() as feed:
        cal = _band_calibration(feed)
    recs = _recommendations(stats, cal, breakdown)

    lines = [f"# Nightly review — {today}", ""]
    lines += [
        "## Paper book",
        f"- open **{stats['open']}** (${stats['open_stake']:.0f})  ·  settled **{stats['settled']}** "
        f"({stats['won']}W / {stats['lost']}L)",
        f"- realized P&L **${stats['realized_pnl']:.2f}**  ·  ROI **{stats['roi']*100:+.1f}%** "
        f"(exp ~+17%)  ·  win **{stats['win_rate']*100:.0f}%** (exp ~24.5%)",
        "",
        "## Edge by price band (out-of-sample, 356k-market universe, 48h horizon)",
        "| band | n | win% | mean px | buy ROI |",
        "|------|---|------|---------|---------|",
    ]
    for b in _BANDS:
        d = cal[b]
        if d["n"]:
            lines.append(f"| {b[0]:.2f}–{b[1]:.2f} | {d['n']} | {d['win_rate']*100:.0f}% | "
                         f"{d['mean_price']:.3f} | {d['buy_roi']*100:+.0f}% |")
    if breakdown:
        lines += ["", "## Paper results by entry price",
                  "| bucket | n | win% | ROI |", "|--------|---|------|-----|"]
        for k, r in breakdown.items():
            lines.append(f"| {k} | {r['n']} | {r['win_rate']*100:.0f}% | {r['roi']*100:+.0f}% |")
    lines += ["", "## Recommendations"]
    lines += [f"{i+1}. {r}" for i, r in enumerate(recs)]

    report = "\n".join(lines)
    os.makedirs(_REPORT_DIR, exist_ok=True)
    path = os.path.join(_REPORT_DIR, f"review-{today}.md")
    with open(path, "w") as f:
        f.write(report + "\n")
    logger.info("review_written", path=path, recommendations=len(recs))

    if send:
        n = PaperNotifier()
        # Headline first, then the full report details as monospace chunks.
        n.send(
            f"🌙 <b>Nightly review — {today}</b>\n"
            f"Settled {stats['settled']} ({stats['won']}W/{stats['lost']}L)  ·  "
            f"ROI {stats['roi']*100:+.0f}%  ·  win {stats['win_rate']*100:.0f}%\n"
            f"Realized ${stats['realized_pnl']:.2f} on ${stats['open_stake']:.0f} open"
        )
        n.send_report(report)
    store.close()
    return report


if __name__ == "__main__":
    print(run_review(send=True))
