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
        "Polymarket markets resolving in **24–96h**; hold to resolution. Fractional-",
        "Kelly sizing on a $150 paper bankroll. NEGATIVE SKEW (~24.5% win rate) — judge",
        "on realized ROI over dozens of settled bets, not the first few.",
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
