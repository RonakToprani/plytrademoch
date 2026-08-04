"""
paper/review.py — Nightly strategy review + recommendations.

Runs every evening (launchd). Three things:
  1. Grades the paper book against the backtest expectation (ROI vs ~+15.7%,
     win rate vs ~27.4%) and breaks results down by entry-price and outcome side.
  2. Re-checks the edge on the cached resolved-market universe across a range of
     price bands — is the live 0.15–0.30 band still the sweet spot, is it
     decaying, is an adjacent slice better? (fast: all from cache, no network.)
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
# Bands to scan for edge (both tokens, cached prices).
_LIVE_BAND = (0.15, 0.30)   # keep in sync with PaperTrader band_lo/band_hi
_BANDS = [(0.02, 0.10), (0.12, 0.15), (0.15, 0.20), (0.15, 0.25), (0.15, 0.30),
          (0.20, 0.30), (0.30, 0.33), (0.33, 0.36), (0.80, 0.90), (0.90, 0.98)]

# What the live config is graded against — the same universe, band and segment
# filter the bot actually trades. See EXPECTATIONS.md.
_EXP_ROI = 0.157
_EXP_WIN = 0.274


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
        from backtest.bigtest import Cell, collect
        from backtest.live import _NO_EDGE_SEGMENTS

        out: dict[tuple, dict] = {}
        for lo, hi in _BANDS:
            # Collect by segment and drop the ones the bot refuses to trade, so the
            # table grades the strategy as configured rather than a universe it no
            # longer buys from.
            cells = collect(lo, hi, horizon=horizon_hours, min_volume=30_000.0,
                            by="segment")
            c = Cell()
            for seg, cell in cells.items():
                if seg in _NO_EDGE_SEGMENTS:
                    continue
                c.n += cell.n
                c.wins += cell.wins
                c.roi_sum += cell.roi_sum
                c.px_sum += cell.px_sum
                c.events |= cell.events
            out[(lo, hi)] = {
                "n": c.n,
                "events": len(c.events),
                "win_rate": c.win_rate,
                "mean_price": c.mean_px,
                "buy_roi": c.roi,
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


def _settled_events(store: PaperStore) -> int:
    """
    Independent settled EVENTS, not bets. This is the sample size that counts:
    correlated legs of one event (bucket sets, ceasefire ladders) are one
    observation, and reporting bets instead is what made a normal losing run look
    like a catastrophe. See EXPECTATIONS.md.
    """
    settled = [b for b in store.all_bets(limit=5000) if b.status in ("WON", "LOST")]
    return len({b.event or f"mk:{b.slug}" for b in settled})


def _paper_breakdown(store: PaperStore) -> dict:
    """Break settled paper bets down by entry-price bucket."""
    settled = [b for b in store.all_bets(limit=5000) if b.status in ("WON", "LOST")]
    # "<0.15" is below the live floor — it exists to keep scoring the legacy bets
    # taken through the old fill_floor leak, which is where nearly all the early
    # losses came from. It should stop growing now that the leak is closed.
    buckets: dict[str, list] = {"<0.15": [], "0.15–0.20": [], "0.20–0.25": [],
                                "0.25–0.30": []}
    for b in settled:
        key = ("<0.15" if b.entry_price < 0.15 else
               "0.15–0.20" if b.entry_price < 0.20 else
               "0.20–0.25" if b.entry_price < 0.25 else "0.25–0.30")
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


def _recommendations(stats: dict, cal: dict, breakdown: dict, events: int) -> list[str]:
    recs: list[str] = []
    settled = stats["settled"]

    # Gate on EVENTS, not bets. EXPECTATIONS.md: distinguishing +16% from 0 at this
    # variance takes ~100+ settled events; below ~30 the honest answer is
    # "not yet knowable", and grading anyway is how a live edge gets switched off.
    if events < 30:
        recs.append(f"SAMPLE: {events} settled EVENTS ({settled} bets) — too few to grade. "
                    f"Keep the {_LIVE_BAND[0]:.2f}–{_LIVE_BAND[1]:.2f} / 6–168h config "
                    "running; a verdict needs ~100 events.")
    else:
        roi, wr = stats["roi"], stats["win_rate"]
        if roi >= _EXP_ROI:
            recs.append(f"ON TRACK: realized ROI {roi*100:+.0f}% is at/above the backtest "
                        f"expectation (~{_EXP_ROI*100:+.0f}%) — no change needed.")
        elif roi >= 0:
            recs.append(f"MARGINAL: realized ROI {roi*100:+.0f}% is positive but below the "
                        f"~{_EXP_ROI*100:+.0f}% backtest expectation — could be variance "
                        "(negative skew) or slippage; keep running, watch win rate.")
        else:
            recs.append(f"UNDERPERFORMING: realized ROI {roi*100:+.0f}% vs "
                        f"~{_EXP_ROI*100:+.0f}% expected over {events} events. "
                        "Check the band table below — if the edge has decayed, tighten.")
        if wr < 0.15:
            recs.append(f"WIN RATE low ({wr*100:.0f}% vs ~{_EXP_WIN*100:.0f}%) — either "
                        "variance or fills are landing badly; check the entry-price table.")

    # The fill leak that produced almost all of the early losses: entries under the
    # band floor, in a slice measured at +2.3% [-7.5,+11.5] — i.e. no edge.
    sub = breakdown.get("<0.15")
    if sub and sub["n"]:
        recs.append(f"LEAK CHECK: {sub['n']} settled bets entered BELOW the "
                    f"{_LIVE_BAND[0]:.2f} floor (ROI {sub['roi']*100:+.0f}%, "
                    f"${sub['pnl']:+.2f}). fill_floor now equals band_lo, so this "
                    "bucket must not grow — if it does, the depth check regressed.")

    # Which live sub-band looks best out-of-sample right now. Compare against
    # _LIVE_BAND rather than a hardcoded pair — the live band moved to 0.15-0.30
    # and hardcoding (0.10, 0.20) made this KeyError once it left _BANDS.
    subbands = {b: cal[b] for b in [(0.15, 0.20), (0.15, 0.25), (0.20, 0.30)]
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

    # Adjacent-strategy signals. The ceiling question: is there edge left just
    # above the band? 0.30-0.33 measured +8.2% [+2.8,+13.0] and 0.33-0.36 +2.5% n.s.,
    # so the answer today is "thin, then gone" — this watches for that changing.
    for hi_band in ((0.30, 0.33), (0.33, 0.36)):
        c2 = cal.get(hi_band)
        if c2 and c2["n"] >= 20:
            verdict = ("still carries edge — consider raising the ceiling"
                       if c2["buy_roi"] > 0.10 else "too thin to add — keep the ceiling")
            recs.append(f"CEILING: {hi_band[0]:.2f}–{hi_band[1]:.2f} {verdict} "
                        f"(ROI {c2['buy_roi']*100:+.0f}%, n={c2['n']}).")
    fav = cal[(0.80, 0.90)]
    if fav["n"] >= 20 and fav["buy_roi"] < -0.05:
        recs.append(f"ADJACENT: strong favorites (0.80–0.90) buy-ROI {fav['buy_roi']*100:+.0f}% "
                    "confirms they're overpriced — a 'fade-the-favorite' (buy the underdog side) "
                    "variant is the same edge from the other end; already captured.")
    low = cal.get((0.12, 0.15))
    if low and low["n"] >= 20:
        verdict = "also underpriced" if low["buy_roi"] > 0.10 else "NOT an edge (efficient/negative)"
        recs.append(f"FLOOR: 0.12–0.15 is {verdict} "
                    f"(ROI {low['buy_roi']*100:+.0f}%, n={low['n']}) — "
                    + ("could extend the band down." if low["buy_roi"] > 0.10
                       else f"keep the {_LIVE_BAND[0]:.2f} floor."))

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
    events = _settled_events(store)
    with DataFeed() as feed:
        cal = _band_calibration(feed)
    recs = _recommendations(stats, cal, breakdown, events)

    lines = [f"# Nightly review — {today}", ""]
    lines += [
        "## Paper book",
        f"- open **{stats['open']}** (${stats['open_stake']:.0f})  ·  settled **{stats['settled']}** "
        f"bets over **{events}** events ({stats['won']}W / {stats['lost']}L)",
        f"- realized P&L **${stats['realized_pnl']:.2f}**  ·  ROI **{stats['roi']*100:+.1f}%** "
        f"(exp ~{_EXP_ROI*100:+.0f}%)  ·  win **{stats['win_rate']*100:.0f}%** "
        f"(exp ~{_EXP_WIN*100:.0f}%)",
        f"- grading gate: **{events}/100** settled events",
        "",
        "## Edge by price band (356k-market universe, 48h, no-edge segments excluded)",
        "| band | n | events | win% | mean px | buy ROI |",
        "|------|---|--------|------|---------|---------|",
    ]
    for b in _BANDS:
        d = cal[b]
        if d["n"]:
            live = " **(live)**" if b == _LIVE_BAND else ""
            lines.append(f"| {b[0]:.2f}–{b[1]:.2f}{live} | {d['n']} | {d['events']} | "
                         f"{d['win_rate']*100:.0f}% | {d['mean_price']:.3f} | "
                         f"{d['buy_roi']*100:+.0f}% |")
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
            f"Settled {stats['settled']} bets / {events} events "
            f"({stats['won']}W/{stats['lost']}L)  ·  "
            f"ROI {stats['roi']*100:+.0f}%  ·  win {stats['win_rate']*100:.0f}%\n"
            f"Realized ${stats['realized_pnl']:.2f} on ${stats['open_stake']:.0f} open"
        )
        n.send_report(report)
    store.close()
    return report


if __name__ == "__main__":
    print(run_review(send=True))
