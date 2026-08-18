"""
paper/review.py — Nightly strategy review + recommendations.

Runs every evening (launchd). Three things:
  1. Grades the paper book against the backtest expectation (ROI vs ~+20.3%,
     win rate vs ~29.6%) and breaks results down by entry-price and outcome side.
  2. Re-checks the edge on the cached resolved-market universe across a range of
     price bands — is the live 0.15–0.33 band still the sweet spot, is it
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
_LIVE_BAND = (0.15, 0.33)   # keep in sync with PaperTrader band_lo/band_hi
_BANDS = [(0.02, 0.10), (0.12, 0.15), (0.15, 0.20), (0.15, 0.25), (0.15, 0.30),
          (0.15, 0.33), (0.20, 0.33), (0.30, 0.33), (0.33, 0.36), (0.36, 0.40),
          (0.80, 0.90), (0.90, 0.98)]
# Bands whose recommendations are gated on significance — only these get the
# (expensive) event-clustered bootstrap: the floor probe, the live band
# headline, and the two ceiling probes.
_CI_BANDS = {(0.12, 0.15), (0.15, 0.33), (0.33, 0.36), (0.36, 0.40)}

# What the live config is graded against — the same universe, band and segment
# filter the bot actually trades (2026-08-05 recalibration on the gated
# universe: game-winner/election/price-barrier/token-launch excluded alongside
# mention-count/fed-macro; 2026-08-17 classifier leak fixes). See EXPECTATIONS.md.
# Re-measured 08-17 on 10,371 in-band rows / 7,304 events @48h, slip 0.01:
# +20.3% [+16.8, +24.0], 29.6% win. Both moved UP because the leaks they removed
# (match-shaped game-winner slugs, season futures, unnamed elections, ECB/BoJ
# decisions) were diluting the blend, not adding to it.
_EXP_ROI = 0.203
_EXP_WIN = 0.296

# Bets opened before this date were placed by a DIFFERENT strategy (game-winner
# flow made up ~85% of the old book) and must not grade the current one. The
# grading gate and ROI verdicts below only count bets opened on/after the epoch;
# the all-time book is still shown for continuity.
_STRATEGY_EPOCH = "2026-08-06"


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
        from backtest.bigtest import Cell, bootstrap_ci, collect
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
                c.obs += cell.obs
            # Event-clustered CI, so the recommendations below can distinguish
            # "measured edge" from "positive-looking noise". Recommending a band
            # change off a point estimate whose CI includes zero is how unproven
            # flow gets bought (the FLOOR rec did exactly that on 2026-08-07/08).
            # Bootstrapped only where a rec is gated on it — the big reference
            # bands (0.02-0.10, 0.80+) would triple the nightly runtime for a
            # CI nothing consumes.
            ci_lo, ci_hi = (bootstrap_ci(c.obs)
                            if (lo, hi) in _CI_BANDS and len(c.events) >= 2
                            else (None, None))
            out[(lo, hi)] = {
                "n": c.n,
                "events": len(c.events),
                "win_rate": c.win_rate,
                "mean_price": c.mean_px,
                "buy_roi": c.roi,
                "ci_lo": ci_lo,
                "ci_hi": ci_hi,
            }
        if any(v["n"] for v in out.values()):
            return out
    except (ImportError, Exception):  # noqa: B014 - fall back to the legacy path
        pass
    return _band_calibration_legacy(feed, horizon_hours)


def _stress_roi(band: tuple[float, float], *, horizon_hours: int = 48,
                slippage: float = 0.03) -> dict | None:
    """
    Gated ROI + event-clustered CI for one band at a punitive slippage.

    The 08-05 recalibration's decision rule was never "is it positive at slip
    0.01" — it was "does it still stand up when you pay a realistic spread".
    Band-change recommendations have to apply the same bar, so they need one
    extra collect at the stress slippage. Returns None if the deep universe
    isn't available (legacy cache path), in which case callers stay silent.
    """
    try:
        from backtest.bigtest import Cell, bootstrap_ci, collect
        from backtest.live import _NO_EDGE_SEGMENTS

        cells = collect(band[0], band[1], horizon=horizon_hours, slippage=slippage,
                        min_volume=30_000.0, by="segment")
        c = Cell()
        for seg, cell in cells.items():
            if seg in _NO_EDGE_SEGMENTS:
                continue
            c.n += cell.n
            c.wins += cell.wins
            c.roi_sum += cell.roi_sum
            c.events |= cell.events
            c.obs += cell.obs
        if c.n < 20 or len(c.events) < 2:
            return None
        ci_lo, ci_hi = bootstrap_ci(c.obs)
        return {"n": c.n, "buy_roi": c.roi, "ci_lo": ci_lo, "ci_hi": ci_hi}
    except Exception:   # noqa: BLE001 — a recommendation must never break the review
        return None


def _ci_text(c: dict) -> str:
    ci = (f", CI [{c['ci_lo']*100:+.0f}%, {c['ci_hi']*100:+.0f}%]"
          if c.get("ci_lo") is not None else "")
    return f"(ROI {c['buy_roi']*100:+.0f}%{ci}, n={c['n']})"


def _band_change_verdict(c: dict, band: tuple[float, float]) -> tuple[bool, str]:
    """
    Should the live band be widened to include `band`? Returns (clears_bar, why).

    Three states, and keeping them distinct is the whole point — the old wording
    collapsed the middle one into "no significant edge" and so printed that
    phrase next to a CI of [+2%, +25%], which is a contradiction that makes every
    other recommendation harder to trust:

      1. CI includes zero            -> no significant edge.
      2. CI excludes zero but the    -> significant, yet too weak to trade: a band
         lower bound is under +3%       change bought on a +1% lower bound is how
         or ROI is under +10%           unproven flow gets into the book.
      3. clears (2) but dies at      -> the 08-05 decision rule. Deep longshots and
         slippage 0.03                  the top of the band are exactly where a
                                        penny of spread eats the whole edge, so
                                        slip 0.01 alone never justifies a change.
    Only a slice that clears all three is worth widening into.
    """
    lo = c.get("ci_lo")
    if lo is None:
        return False, "has no significance estimate"
    if lo <= 0:
        return False, "has no significant edge"
    if lo <= 0.03 or c["buy_roi"] <= 0.10:
        return False, "is significant but below the bar for a band change (CI floor >+3%, ROI >+10%)"
    stress = _stress_roi(band, horizon_hours=48, slippage=0.03)
    if stress is None:
        return False, "clears the bar at slip 0.01 but could not be stress-tested at 0.03"
    if stress["ci_lo"] is None or stress["ci_lo"] <= 0:
        return False, ("clears the bar at slip 0.01 but does NOT survive the slip-0.03 "
                       f"stress test ({stress['buy_roi']*100:+.0f}%)")
    return True, ("clears the bar AND survives slip 0.03 "
                  f"({stress['buy_roi']*100:+.0f}%)")


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
            "events": n,        # legacy path has no event keys; bets ≈ events
            "win_rate": (a["win"] / n) if n else 0.0,
            "mean_price": (a["psum"] / n) if n else 0.0,
            "buy_roi": (a["roi"] / n) if n else 0.0,
            "ci_lo": None,      # no cluster bootstrap on the legacy path —
            "ci_hi": None,      # significance-gated recs stay silent
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


def _epoch_stats(store: PaperStore) -> dict:
    """Settled results for bets opened on/after _STRATEGY_EPOCH — the only
    sample that tests the currently-configured strategy."""
    settled = [b for b in store.all_bets(limit=5000)
               if b.status in ("WON", "LOST") and b.opened_at >= _STRATEGY_EPOCH]
    stake = sum(b.stake_usd for b in settled)
    pnl = sum(b.pnl or 0.0 for b in settled)
    wins = sum(1 for b in settled if b.status == "WON")
    return {
        "settled": len(settled),
        "events": len({b.event or f"mk:{b.slug}" for b in settled}),
        "won": wins,
        "lost": len(settled) - wins,
        "roi": (pnl / stake) if stake else 0.0,
        "win_rate": (wins / len(settled)) if settled else 0.0,
        "realized_pnl": pnl,
    }


def _paper_breakdown(store: PaperStore) -> dict:
    """Break settled paper bets down by entry-price bucket."""
    settled = [b for b in store.all_bets(limit=5000) if b.status in ("WON", "LOST")]
    # "<0.15" is below the live floor — it exists to keep scoring the legacy bets
    # taken through the old fill_floor leak, which is where nearly all the early
    # losses came from. It should stop growing now that the leak is closed.
    buckets: dict[str, list] = {"<0.15": [], "0.15–0.20": [], "0.20–0.25": [],
                                "0.25–0.30": [], "0.30–0.33": []}
    for b in settled:
        key = ("<0.15" if b.entry_price < 0.15 else
               "0.15–0.20" if b.entry_price < 0.20 else
               "0.20–0.25" if b.entry_price < 0.25 else
               "0.25–0.30" if b.entry_price < 0.30 else "0.30–0.33")
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


def _recommendations(ep: dict, cal: dict, breakdown: dict) -> list[str]:
    recs: list[str] = []
    # Grade ONLY the post-epoch sample — earlier bets were placed by a strategy
    # (game-winner flow) the scanner no longer runs.
    events, settled = ep["events"], ep["settled"]

    # Gate on EVENTS, not bets. EXPECTATIONS.md: distinguishing +20% from 0 at this
    # variance takes ~100+ settled events; below ~30 the honest answer is
    # "not yet knowable", and grading anyway is how a live edge gets switched off.
    if events < 30:
        recs.append(f"SAMPLE: {events} settled EVENTS ({settled} bets) since the "
                    f"{_STRATEGY_EPOCH} strategy epoch — too few to grade. "
                    f"Keep the {_LIVE_BAND[0]:.2f}–{_LIVE_BAND[1]:.2f} / 6–168h config "
                    "running; a verdict needs ~100 events.")
    else:
        roi, wr = ep["roi"], ep["win_rate"]
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

    # Which live sub-band looks best out-of-sample right now. FLOW-ADJUSTED:
    # total profit is ROI x independent events, and flow is this book's binding
    # constraint — the wide band was chosen precisely because 0.15-0.20's higher
    # per-bet ROI rides on half the events. A narrowing rec must clear the bar
    # on expected TOTAL profit (roi x events), not per-bet ROI, or it just
    # re-litigates the flow-vs-ROI decision every night.
    subbands = {b: cal[b] for b in [(0.15, 0.20), (0.15, 0.25), (0.15, 0.30),
                                    (0.20, 0.33)]
                if b in cal and cal[b]["n"] >= 20}
    live = cal.get(_LIVE_BAND)
    if subbands and live:
        best = max(subbands, key=lambda b: subbands[b]["buy_roi"])
        bd = cal[best]
        flow_frac = bd["events"] / max(live["events"], 1)
        beats_total = bd["buy_roi"] * bd["events"] > live["buy_roi"] * live["events"]
        recs.append(f"BAND: {best[0]:.2f}–{best[1]:.2f} leads per-bet out-of-sample "
                    f"(win {bd['win_rate']*100:.0f}%, ROI {bd['buy_roi']*100:+.0f}%, "
                    f"n={bd['n']}) on {flow_frac*100:.0f}% of the live band's events. "
                    + ("Flow-adjusted it beats the live band — consider narrowing."
                       if best != _LIVE_BAND and beats_total
                       else f"Flow-adjusted, the {_LIVE_BAND[0]:.2f}–{_LIVE_BAND[1]:.2f} "
                            "band still wins on total expected profit — keep it."))

    # Adjacent-strategy signals. The ceiling question: is there edge left just
    # above the band? On the gated universe 0.30-0.33 is in the band (+10.7%
    # [+4.5,+17.5]); 0.33-0.36 is dead (+3.7% n.s.) — this watches for change.
    # A raise needs a SIGNIFICANT slice (event-clustered CI floor above +3%),
    # not a hopeful point estimate.
    for hi_band in ((0.33, 0.36), (0.36, 0.40)):
        c2 = cal.get(hi_band)
        if c2 and c2["n"] >= 20:
            clears, why = _band_change_verdict(c2, hi_band)
            action = "consider raising the ceiling" if clears else "keep the ceiling"
            recs.append(f"CEILING: {hi_band[0]:.2f}–{hi_band[1]:.2f} {_ci_text(c2)} "
                        f"{why} — {action}.")
    fav = cal[(0.80, 0.90)]
    if fav["n"] >= 20 and fav["buy_roi"] < -0.05:
        recs.append(f"ADJACENT: strong favorites (0.80–0.90) buy-ROI {fav['buy_roi']*100:+.0f}% "
                    "confirms they're overpriced — a 'fade-the-favorite' (buy the underdog side) "
                    "variant is the same edge from the other end; already captured.")
    low = cal.get((0.12, 0.15))
    if low and low["n"] >= 20:
        # On 2026-08-07/08 this rec said "could extend the band down" off +10%
        # whose CI was [-1.4, +20.6] — i.e. noise. A floor extension needs the
        # CI floor above +3%, same bar as the ceiling.
        #
        # It also needs to SURVIVE THE SPREAD, and that is the check this rec was
        # missing. After the 08-17 classifier fixes the slice turned significant
        # at slip 0.01 (+13.3% [+1.4, +25.7]) while still dying at slip 0.03
        # (-0.6% n.s.) — and the old wording printed "has no significant edge"
        # next to a CI that excluded zero, contradicting itself. Deep longshots
        # are exactly where a penny of spread costs the most, so the 0.03 stress
        # test is the decision rule; slip 0.01 alone is not.
        clears, why = _band_change_verdict(low, (0.12, 0.15))
        action = ("consider extending the band down" if clears
                  else f"keep the {_LIVE_BAND[0]:.2f} floor")
        recs.append(f"FLOOR: 0.12–0.15 {_ci_text(low)} {why} — {action}.")

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
    ep = _epoch_stats(store)
    with DataFeed() as feed:
        cal = _band_calibration(feed)
    recs = _recommendations(ep, cal, breakdown)

    lines = [f"# Nightly review — {today}", ""]
    lines += [
        "## Paper book",
        f"- open **{stats['open']}** (${stats['open_stake']:.0f})  ·  settled **{stats['settled']}** "
        f"bets over **{events}** events ({stats['won']}W / {stats['lost']}L)",
        f"- realized P&L **${stats['realized_pnl']:.2f}**  ·  ROI **{stats['roi']*100:+.1f}%** "
        f"(exp ~{_EXP_ROI*100:+.0f}%)  ·  win **{stats['win_rate']*100:.0f}%** "
        f"(exp ~{_EXP_WIN*100:.0f}%)",
        f"- since strategy epoch {_STRATEGY_EPOCH}: settled **{ep['settled']}** bets / "
        f"**{ep['events']}** events ({ep['won']}W / {ep['lost']}L)  ·  "
        f"P&L **${ep['realized_pnl']:.2f}**  ·  ROI **{ep['roi']*100:+.1f}%**",
        f"- grading gate: **{ep['events']}/100** settled events since epoch "
        f"(all-time: {events})",
        "",
        "## Edge by price band (356k-market universe, 48h, no-edge segments excluded)",
        "| band | n | events | win% | mean px | buy ROI | 95% CI (event-clustered) |",
        "|------|---|--------|------|---------|---------|--------------------------|",
    ]
    for b in _BANDS:
        d = cal[b]
        if d["n"]:
            live = " **(live)**" if b == _LIVE_BAND else ""
            ci = (f"[{d['ci_lo']*100:+.0f}%, {d['ci_hi']*100:+.0f}%]"
                  if d.get("ci_lo") is not None else "—")
            lines.append(f"| {b[0]:.2f}–{b[1]:.2f}{live} | {d['n']} | {d['events']} | "
                         f"{d['win_rate']*100:.0f}% | {d['mean_price']:.3f} | "
                         f"{d['buy_roi']*100:+.0f}% | {ci} |")
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
