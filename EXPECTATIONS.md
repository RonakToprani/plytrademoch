# Strategy expectations — what "working" looks like

Last recalibrated **2026-08-05**, classifier re-audited **2026-08-17**, on
355,896 resolved markets / 218,734 events. Anything grading this strategy — the
nightly review, the scheduled cloud reviewer, or a human looking at the
dashboard — should use the numbers here.

## The numbers

| Quantity | Expect | Notes |
|---|---|---|
| Entry band | **0.15 – 0.33** | the only slice surviving the slip-0.03 stress gate; floor and ceiling re-confirmed 08-17 (below) |
| Segments | **include** other, game-prop, geopolitics, crypto-price; **exclude** game-winner, mention-count, fed-macro, election, price-barrier, token-launch, sports-season | the 08-05/08-06 recalibration, with the 08-17 leak fixes; see below |
| Win rate | **~29.6%** | in-band, gated universe |
| ROI per bet | **~+20.3%** | 95% CI [+16.8%, +24.0%], n=10,371 / 7,304 events @48h |
| Cost robustness | **+10.9% [+7.7, +14.4] at slippage 0.03** | the old ungated blend went ~0 at 0.03 — this one survives |
| Hold window | **6 – 168h** (geopolitics: **6 – 240h**) | decay measured 08-06: +13.2% @168h → +10.0% @240h → +0.8% n.s. @336h; geopolitics alone is EDGE at 240h at both slippages |
| Kelly input | **calibrated q(price)**, 0.25 multiple | refit 08-05 on the gated universe; sizing only, go/no-go is price-in-band |
| Paper bankroll | **$1,000** | unchanged |
| Strategy epoch | **2026-08-06** | only bets opened on/after this date test this strategy |

Retired figures: "+50–70% ROI" (n=126, 2026-07), "+15.7% [+12.5, +18.9]"
(2026-08-03, ungated blend) and "+19.8% [+16.2, +23.3]" (2026-08-05 — the right
gate, but leakily implemented; see the 08-17 audit). The ungated blend was real
but unreachable: its average was carried by segments the live filters almost
never surfaced, while ~85% of actual flow came from segments with no edge at
all (see below).

## The 2026-08-17 finding: the gate was right, the classifier leaked

The 08-05 segment gate is only as good as the slug patterns implementing it, and
an audit of what actually reached the buyable `other` bucket found four leaks.
All four were markets the gate *intends* to exclude that simply did not match
their segment's regex:

| leak | scale | measured, band 0.15–0.33 @48h |
|---|---|---|
| **match-shaped game-winner** — the league whitelist enumerated ~30 prefixes and missed cbb, cfb, sea, bun, fl1, fif, bra, crint, spl, tur, uef, ere, arg, por, mex, col, es2, aus, bl2, lib, bkcba, j1100, itf, … | 10,577 slugs / 2,841 in-band rows — **48% of the `other` bucket** | +12.3% [+5.7, +19.1] @0.01 but **+3.8% [−2.2, +10.1] n.s. @0.03** — the game-winner signature, failing the same stress gate that excluded the class |
| **season/tournament futures** beyond the four US majors: F1 titles, LCK/LPL playoffs, CS2 EWC, NBA conference finals, `*-of-the-year` awards, "champion on \<date\>" | 266 slugs (20 live in-band) | −12.3% @0.01, −19.2% @0.03 on the leaked slice; class measured −54.5% [−87.7, −11.0] @168h |
| **elections that never say "election"** — "win the Maine **senate race**", "…-race-in-2026", "win an absolute majority", "win the most seats" | 7 live in-band midterm markets | class excluded on the poll/model-anchor argument; +9.1% n.s. at best, −8.5% @0.03 |
| **central-bank rate decisions** the `^fed-` prefix missed — fed-funds-target levels, ECB/BoJ/BoE meeting outcomes | 80 slugs (10 live in-band) | class measured −17.3% |

Fixing them **raises** the gated blend, because every leak was diluting it:

| | slip 0.01 | slip 0.02 | slip 0.03 |
|---|---|---|---|
| gated blend, leaky classifier | +18.6% [+15.5, +21.9] | — | +9.4% [+6.6, +12.4] |
| gated blend, fixed classifier | **+20.3% [+16.8, +24.0]** | +15.4% [+12.0, +19.0] | **+10.9% [+7.7, +14.4]** |

The forward risk mattered more than the 1.7-point uplift. None of the leaked
markets were in-window on 08-17 (all resolve past 168h), so the fix cost **zero**
current flow — but European football and college seasons restart within weeks,
and the seven midterm markets all resolve on the *same November date*, where the
≤25%-of-bankroll-per-resolution-date cap would have pushed a quarter of the book
into one excluded segment in a single week. Left alone this would have quietly
reproduced the pre-epoch failure mode (85% of flow in game-winner markets).

**The live book confirms it.** Splitting the 40 post-epoch settled bets with the
fixed classifier: 8 of them were match-shaped game-winner markets the old
whitelist missed (`col1-`, `lec-`, `itf-`, `crint-`, `clf-` — Colombian and
Mexican league, ITF tennis, cricket internationals, Bundesliga), and they went
1W/7L for **−$79.85 on $135.12 staked**. The remaining book ran **+37.1%**
against the traded figure of +17.7%. Treat the *size* of that gap as noise —
n=8, and the backtest says this class is worth ~0, not −59% — but the leak
itself was real, live, and taking ~20% of post-epoch flow.

The classifier now matches the match **shape** (`league-team-team-YYYY-MM-DD`)
rather than a league whitelist that can never be complete, and all four leaks are
pinned by `tests/test_segments.py`. Note the deliberate non-fix: central-bank
*personnel* markets ("Powell out as Fed chair") stay tradeable — the exclusion
argument is the futures curve, and there isn't one behind a resignation.

**The Kelly curve did not need refitting.** Re-measured on the cleaned universe,
`calibrated_win_rate(p)` is within ~1 point of realised win% at every slice
(0.163 → 21.1% model vs 21.2% actual; 0.253 → 30.9% vs 31.1%; 0.313 → 35.8% vs
36.7%), so sizing is unchanged.

**Band floor and ceiling re-confirmed** on the cleaned universe — 0.15–0.33 is
the only slice that survives the slip-0.03 stress gate:

| slice | slip 0.01 | slip 0.02 | slip 0.03 |
|---|---|---|---|
| 0.12–0.15 | +13.3% [+1.4, +25.7] EDGE | +5.9% n.s. | **−0.6% n.s.** → floor stays |
| **0.15–0.33** | **+20.3% EDGE** | **+15.4% EDGE** | **+10.9% EDGE** |
| 0.33–0.36 | +6.5% n.s. | +3.6% n.s. | +0.8% n.s. → ceiling stays |

Note the trap in row one: on the cleaned universe 0.12–0.15 *does* turn
significant at slip 0.01 (it was n.s. before). It still dies by 0.03, and the
live book's own sub-floor fills realised −54% over n=17, so the floor holds.

## The 2026-08-05 finding: structure, not sport — and not the blend

The 08-03 calibration measured the edge as one blended number over everything
except mention-count/fed-macro. Fresh-eyes decomposition showed that blend was
an average over sub-populations with completely different economics, and that
the live scanner's filters (≥$30k volume, 6–168h window) systematically served
the book the WORST slice of it:

| class @6h, band 0.15–0.30 | slip 0.01 | slip 0.03 | verdict |
|---|---|---|---|
| game-**winner** (who wins the game/match/series — all sports, esports, cricket, tennis, UFC) | +7.6% [+2.5, +13.0] | **−0.8% n.s.** | **no edge net of spread — excluded** |
| game-**prop** (draws, exact scores, totals, spreads) | +18.2% [+10.7, +25.7] | **+8.9% EDGE** | kept |
| true-other (one-off questions) | +20.4% [+15.5, +25.3] | +10.8% EDGE | kept |
| geopolitics | +68.5% [+34.6, +101.9] | +55.1% EDGE | kept (thin n) |
| crypto-price | +11.5% [+2.8, +20.6] @0.01 | n.s. at 0.03, but crypto books are pennies wide so 0.01 is the realistic cost | kept, watch |
| tennis / ufc-boxing / election / price-barrier / token-launch | n.s. to negative everywhere | negative | excluded |

The economics: **winner markets have an external anchor** — sharp sportsbook
odds — so Polymarket prices them efficiently and the favorite-longshot bias is
already arbitraged away; whatever is left dies to the spread. Props, score
structures, and one-off questions have no anchor, and that is where the bias
survives. Same logic that killed mention-count (tweet counters) and fed-macro
(fed-funds futures) on 08-03: **anything with a public mechanical anchor is
calibrated; anything without one is not.** Election joins the excluded list on
the same argument (poll/model anchor; +9.1% n.s. at best, −8.5% at slip 0.03).

Stability: the winner/prop split holds at 6h, 24h and 48h horizons, and the
gated blend is a significant EDGE at every horizon 6–168h and every slippage
0.01/0.02/0.03.

This resolved the "UNDERPERFORMING" verdict the nightly review reached on
2026-08-06 (−18.5% over 103 events): the post-fix book was 48/56 game-winner
bets which realized ≈ +1.2% — exactly what the recalibration says that flow is
worth — plus early losses from the two 08-03 plumbing bugs. The book was not
running the measured strategy; now it is.

## The price curve — gated universe, 48h, slip 0.01

| slice | n | events | win% | mean px | ROI | 95% CI | |
|---|---|---|---|---|---|---|---|
| 0.12–0.15 | 2,048 | 1,780 | 15.6% | 0.133 | +9.5% | [−1.4%, +20.6%] | **not significant — below floor** |
| 0.15–0.18 | 2,048 | 1,879 | 21.1% | 0.163 | +22.2% | [+11.5%, +32.5%] | |
| 0.18–0.21 | 2,013 | 1,854 | 25.2% | 0.193 | **+24.4%** | [+15.0%, +33.7%] | sweet spot |
| 0.21–0.24 | 2,253 | 2,105 | 28.9% | 0.223 | **+23.5%** | [+15.5%, +31.4%] | sweet spot |
| 0.24–0.27 | 2,476 | 2,330 | 30.9% | 0.253 | +17.5% | [+10.5%, +24.4%] | |
| 0.27–0.30 | 2,460 | 2,310 | 33.0% | 0.282 | +12.7% | [+6.6%, +19.2%] | |
| 0.30–0.33 | 2,021 | 1,882 | 35.8% | 0.313 | +10.7% | [+4.5%, +17.5%] | band ceiling (in band since 08-05) |
| 0.33–0.36 | 1,917 | 1,788 | 36.6% | 0.343 | +3.7% | [−2.2%, +9.9%] | **dead** |

Read it as a curve: edge switches on at 0.15, peaks 0.18–0.24, decays through
0.33, gone by 0.36. The ceiling moved 0.30 → 0.33 because on the gated flow the
slice is solidly positive (lower CI +4.5%) and the game-winner gate makes flow
scarcer — the marginal 0.30–0.33 bet buys back sample at a still-healthy ROI.
Kelly sizes it down automatically (f: 0.080 at 0.21 → 0.056 at 0.33).

Sizing follows this curve via `backtest.live.calibrated_win_rate` (refit 08-05).
The flat-win-rate inversion bug and the "round sub-$1 stakes up" bug remain
fixed and guarded by tests.

## How to judge results — read this before calling the strategy broken

**Only bets opened on/after 2026-08-06 test this strategy.** Everything earlier
was a different book: pre-08-04 had the sub-floor-fill and stale-settlement
bugs; 08-04/08-05 ran the fixed plumbing on unmeasured game-winner flow. The
nightly review now grades post-epoch only.

**Count settled *events*, not settled bets.** Correlated legs are one
observation. The event-key guard (one open bet per event, held across cycles)
and the ≤25%-of-bankroll-per-resolution-date guard remain in force.

**Negative skew means long losing runs are normal.** At ~28% win, 10 straight
losses has probability ~3.7%. Judge on realized ROI over dozens of settled
events. Distinguishing +20% from 0 takes roughly 80–100 settled events; below
~30 the honest answer is "not yet knowable."

**Check that settlement is actually running before reading any P&L.** The
stale-cache failure of 08-03 (16 resolved bets held open, 3 hidden wins) is
fixed — TTL 1h, forced refresh past `resolves_at` — but the lesson stands: a
metric that can only move in one direction is a bug until proven otherwise.

## Flow is a real constraint — and the gate makes it tighter

The game-winner gate removes the recurring daily flow (MLB/esports/tennis) that
was filling the book. What remains recurs more slowly: props post with the
games, one-off questions and geopolitics arrive on news. Watch
`grep paper_cycle_done logs/cycle.log | tail` — sustained `opened=0` with a
book below the exposure cap now means the flow levers below need pulling, not
that the edge is gone.

Flow levers, measured 2026-08-06:
1. **The $10k–30k volume tier is DEAD — measured, closed.** Priced all 141k
   markets and the gated edge does not exist there: −5.9% [−9.0, −2.7] @48h
   slip 0.01, −13.0% at slip 0.03, negative even for `other` (−8.6%). The
   volume gradient is monotone: 10–30k dead → 30–60k +13.1% EDGE → 60–100k
   +19.7% → ≥100k +22.5%. **Edge RISES with volume** — the bias needs real
   retail flow, and thin markets' mid prices aren't fillable anyway. min_volume
   stays $30k; for future capital scaling this is good news (the edge
   concentrates where the capacity is).
2. **The 168–336h window — measured, mostly closed.** The gated blend decays
   +13.2% [+8.8, +17.6] @168h → +10.0% [+5.2, +15.1] @240h → +0.8% n.s. @336h,
   and only 168h survives slip 0.03. Per segment: `other` and `game-prop` are
   done past 168h. **Geopolitics is the exception and got a per-segment 240h
   window** (`_SEGMENT_MAX_HOURS`): +41.1% [+16.3, +69.3] @240h slip 0.01 and
   still +29.5% [+6.9, +55.3] at slip 0.03 (n=182 events). 336h fails the
   stress gate (+20.3% n.s.) and was not extended to.
   Bonus finding from the sweep: **sports-season futures are toxic in-window**
   (−54.5% [−87.7, −11.0] @168h) and joined the excluded segments.
3. **Prop coverage — measured 2026-08-17, and CLOSED.** This was the last named
   flow lever, so it was worth doing properly: every prop-shaped suffix sitting
   inside the excluded game-winner class was enumerated and priced. None of them
   is a game-prop economically. Against the `game-prop` baseline of +29.4%
   [+23.9, +34.8] @0.01 / +19.6% [+14.6, +24.6] @0.03:

   | family | n | ROI @0.01 | ROI @0.03 |
   |---|---|---|---|
   | `team-total-{home,away}-Npt5` | 202 | −17.4% [−37.7, +4.7] n.s. | **−23.7% [−42.4, −3.5] NEGATIVE** |
   | `halftime-result-{home,away}` | 77 | +1.6% n.s. | −6.9% n.s. |
   | `first-to-score-{home,away,neither}` | 36 | +7.6% n.s. | −1.3% n.s. |
   | `total-games-Npt5`, `set-totals`, `totals-Npt5`, `kill-over`, `team-to-advance` | 1–16 each | too thin to price | too thin to price |

   The read: a *team* total is a sportsbook line like any other — anchored, and
   negative once you pay the spread. Only the score-STRUCTURE props already in
   the class (draws, exact scores, match totals) carry the bias. Do not add
   these families; adding `team-total` would have been actively costly.

   With the volume floor, the hold window and prop coverage all now measured and
   closed, **there is no known unexploited flow left**. ~2–3 entries a day at
   ≥$30k volume is the edge's actual capacity, not a symptom of a broken filter.

## Known open questions

- **Cricket props/winners and esports props are thin or unmeasured** at ≥$30k;
  esports *winners* measured +8.7% n.s. at slip 0.03 and are excluded with the
  rest of game-winner. The 10k–30k tier turned out to be dead across the board,
  so no rescue for these segments from below the volume floor.
- **Soccer props carry the biggest measured edge** (+22.3% at slip 0.03) but
  draws/exact-scores are exactly where a stale-mid artifact would look best;
  the paper book (live depth-checked fills) is the arbiter. Watch the game-prop
  realized bucket specifically.
- **2024 is negative** for the old band on a thin sample; unchecked on the
  gated universe. Worth a by-year split of the gated flow.
- **Geopolitics +55–68%** is on only ~150 events — real but don't size a thesis
  on it alone.

## Reproducing

```bash
python -m backtest.universe            # build resolved_deep via Gamma keyset
python -m backtest.bigtest fetch       # price every token at each horizon
python -m backtest.bigtest report      # band curve + segments + by-year
python -m paper.run review             # grade the live book against this file
```

Every number in this document comes from `backtest.bigtest.collect` +
`bootstrap_ci` (event-clustered), volume ≥ $30k, horizon 48h and slippage 0.01
unless stated otherwise. The 08-05 fine-segment and structure splits were run
with the same machinery over `resolved_deep` + `horizon_price`; the segment
classifier now lives in `backtest.bigtest._SEGMENTS` and is pinned by
`tests/test_segments.py`.
