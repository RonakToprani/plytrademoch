# plytrademoch — Polymarket underdog strategy (paper trading)

A measurement-first trading research project on Polymarket. The live system
paper-trades a single validated edge: **buy underdog outcome tokens priced
0.15–0.33 in markets without an external pricing anchor**, hold to resolution.
No real orders are ever placed (DRY-RUN throughout).

**[`EXPECTATIONS.md`](EXPECTATIONS.md) is the source of truth** for what
"working" looks like — every number the strategy is graded against lives there,
recalibrated 2026-08-05/06 on 355,896 resolved markets / 218,734 events.

## The edge, in one paragraph

Favorite–longshot bias exists on Polymarket, but only where prices have no
public anchor. Markets tethered to an external reference — sportsbook odds
(game winners), fed-funds futures (Fed decisions), polls (elections), public
counters (tweet counts) — are efficiently priced, and any residue dies to the
spread. Unanchored markets — one-off questions, game props (draws / exact
scores / totals), geopolitics — keep the bias: underdogs priced 0.15–0.33 win
more than their price implies. Gated blend: **+19.8% ROI per bet
[+16.2%, +23.3]**, ~28.2% win rate, still **+10.1%** under punitive slippage
assumptions (0.03), significant at every hold horizon 6–168h. The edge *rises*
with market volume (dead below $30k, +22.5% above $100k) and decays past 168h
for everything except geopolitics (extended to 240h, measured).

## Project timeline

| period | what happened |
|---|---|
| 2026-03 | Initial build: whale copy-trading bot (scanner, risk engine, dashboard) |
| 2026-07 | Backtest killed the copy-trading thesis (no edge). Pivot to structural edges; underdog band identified and validated; paper-trading system launched on launchd |
| 2026-08-01→03 | First live audits: settlement-cache bug, Kelly sizing inversion, sub-floor fill leak — found and fixed; big-sample recalibration (356k markets, event-clustered bootstrap) |
| 2026-08-05→06 | Structural recalibration: game-winner flow measured dead and gated out, band 0.15→0.33, $10k–30k volume tier measured dead, per-segment 240h window for geopolitics |
| 2026-08-08 | Recommendation engine made significance- and flow-aware; repo cleaned of the retired copy-trading system |

## Layout

```
EXPECTATIONS.md      what "working" looks like — read before grading anything
backtest/            research: universe builder, horizon pricer, calibration
  bigtest.py           356k-market calibration + segment classifier + bootstrap
  live.py              live opportunity scanner (band, segments, Kelly sizing)
  datafeed.py          Gamma/CLOB access with caching
  FINDINGS.md          research log (§1 copy-trading rejection still valid;
                       §2–3 superseded by EXPECTATIONS.md)
paper/               the live paper-trading system
  engine.py            one idempotent cycle: settle, scan, depth-verify, record
  store.py             SQLite book (paper_underdog.db)
  review.py            nightly grading + rule-based recommendations
  dashboard.py         one-page monitor (port 8060)
  export.py / inbox.py state snapshot for the cloud reviewer / Telegram inbox
deploy/              launchd plists (cycle 30min, export 3h, review nightly)
config/ utils/       settings (.env-driven) and structlog setup
tests/               classifier, sizing, scanner, depth, paper-engine guards
reports/             state.md snapshot (tracked) + nightly reviews (untracked)
```

## Running

```bash
python -m paper.run cycle        # one settle+scan cycle (what launchd runs)
python -m paper.run stats        # book summary
python -m paper.run review       # nightly review + recommendations
python -m paper.run dashboard    # monitor on :8060

python -m backtest.universe      # rebuild resolved-market universe (Gamma)
python -m backtest.bigtest fetch # price tokens at each horizon (CLOB)
python -m backtest.bigtest report# calibration: band curve, segments, years
pytest                           # test suite
```

Operations notes: the Mac must stay awake (sleep silently stalls launchd
timers — check `logs/cycle.log` timestamps, not the dashboard). A nightly
cloud reviewer (Claude routine) reads `EXPECTATIONS.md` + `reports/state.md`
and sends a Telegram verdict; its embedded spec must be updated whenever the
strategy is recalibrated.

## Judging results — the rules that keep burning people

- **Only bets opened on/after the strategy epoch (2026-08-06)** test the
  current configuration.
- **Count settled events, not bets** — correlated legs are one observation.
- ~28% win rate means long losing streaks are normal; a verdict needs
  ~80–100 settled events. Below ~30 the honest answer is "not yet knowable".
- A quiet book is not a broken book: every flow lever beyond the current
  filters has been measured and found dead. Do not loosen filters into
  measured-negative flow to look busy.
