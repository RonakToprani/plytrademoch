"""
paper/export.py — Export a paper-strategy state snapshot for the cloud reviewer.

Cloud routines can't read the local DB, so we write a self-contained markdown
snapshot (book, P&L, open/settled bets, edge-by-band, params) that gets committed
to the repo. The scheduled Opus routine reads this file to write its review.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from backtest.datafeed import DataFeed
from paper.review import _BANDS, _band_calibration, _paper_breakdown
from paper.store import PaperStore


def write_state(path: str = "reports/state.md") -> str:
    store = PaperStore()
    s = store.stats()
    opens = store.open_bets()
    settled = [b for b in store.all_bets(limit=500) if b.status in ("WON", "LOST", "VOID")]
    breakdown = _paper_breakdown(store)
    last_scan = store.last_scan() or "never"
    store.close()
    with DataFeed() as feed:
        cal = _band_calibration(feed)

    L = [
        f"# Poly underdog paper state — {datetime.now(timezone.utc).isoformat()}",
        "",
        "**Strategy:** buy the underdog outcome token priced **0.15–0.25** on liquid",
        "Polymarket markets resolving in **6–96h**; hold to resolution. Fractional-",
        "Kelly sizing on a $150 paper bankroll. NEGATIVE SKEW (~24.5% win rate) — judge",
        "on realized ROI over dozens of settled EVENTS, not bets and not the first few.",
        "",
        "**Read `EXPECTATIONS.md` in this repo before grading these results.** It is the",
        "source of truth for what 'working' looks like, recalibrated 2026-07-31 on",
        "355,896 markets / 218,734 events. Key points a reviewer must not get wrong:",
        "",
        "- Expect **~+17% ROI** (95% CI [+12.6%, +20.8%]) and a **~24.5% win rate**.",
        "  The older '+50–70% ROI / ~27% win' figures came from n=126 and are RETIRED —",
        "  grading against them marks an on-spec strategy as underperforming.",
        "- **Count settled EVENTS, not bets.** Correlated legs are not independent",
        "  observations: 38 early paper bets spanned only 13 events, and a -50% result",
        "  that looked catastrophic was P=59.6% under a real edge. Bets now carry an",
        "  `event` key and only one open bet per event is allowed.",
        "- **Losing streaks are expected.** At ~24.5% win, 10 straight losses has",
        "  probability ~6.4%. Distinguishing +17% from 0 needs ~100+ settled events;",
        "  below ~30 the honest answer is 'not yet knowable'.",
        "",
        "## Book",
        f"- open **{s['open']}** (${s['open_stake']:.2f})  ·  settled **{s['settled']}** "
        f"({s['won']}W / {s['lost']}L)",
        f"- realized P&L **${s['realized_pnl']:.2f}**  ·  ROI **{s['roi']*100:+.1f}%** "
        f"(backtest exp ~+17%)  ·  win **{s['win_rate']*100:.0f}%** (exp ~24.5%)",
        f"- last scan: {last_scan}",
        "",
        "## Open positions",
        "| market | side | entry | stake | resolves |",
        "|---|---|---|---|---|",
    ]
    for b in opens[:40]:
        L.append(f"| {(b.question or b.slug)[:52]} | {b.outcome} | {b.entry_price:.3f} "
                 f"| ${b.stake_usd:.2f} | {b.resolves_at or ''} |")
    L += ["", "## Settled", "| market | result | P&L |", "|---|---|---|"]
    for b in settled[:60]:
        L.append(f"| {(b.question or b.slug)[:52]} | {b.status} | {(b.pnl or 0):+.2f} |")
    L += ["", "## Edge by price band (out-of-sample, cached universe, 48h horizon)",
          "| band | n | win% | mean px | buy ROI |", "|---|---|---|---|---|"]
    for band in _BANDS:
        d = cal[band]
        if d["n"]:
            L.append(f"| {band[0]:.2f}–{band[1]:.2f} | {d['n']} | {d['win_rate']*100:.0f}% "
                     f"| {d['mean_price']:.3f} | {d['buy_roi']*100:+.0f}% |")
    if breakdown:
        L += ["", "## Paper results by entry price", "| bucket | n | win% | ROI |",
              "|---|---|---|---|"]
        for k, r in breakdown.items():
            L.append(f"| {k} | {r['n']} | {r['win_rate']*100:.0f}% | {r['roi']*100:+.0f}% |")

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    return path
