# Strategy expectations — what "working" looks like

Last recalibrated **2026-08-03** on 355,896 resolved markets / 218,734 events.
Anything grading this strategy — the nightly review, the scheduled cloud
reviewer, or a human looking at the dashboard — should use the numbers here.

## The numbers

| Quantity | Expect | Notes |
|---|---|---|
| Entry band | **0.15 – 0.30** | 0.10–0.20 → 0.15–0.25 (07-31) → 0.15–0.30 (08-03), for FLOW |
| Segments | **exclude `mention-count`, `fed-macro`** | measured negative; see below |
| Win rate | **~27.4%** | in-band, excluding the two dead segments |
| ROI per bet | **~+15.7%** | 95% CI [+12.5%, +18.9%], n=15,407 / 11,133 events |
| Hold window | **6 – 168h** | ceiling raised from 96h on 2026-08-03, for FLOW |
| Kelly input | **calibrated q(price)**, 0.25 multiple | sizing only; go/no-go is price-in-band |
| Paper bankroll | **$1,000** | raised from $150 on 2026-08-03 so Kelly stakes clear the $1 ticket |

**The old "+50–70% ROI, ~27% win rate" figures are retired.** They came from a
126-observation sample and were never precise enough to support that confidence.
Grading against them marks a perfectly on-spec strategy as "UNDERPERFORMING".

## The price curve — this is the whole strategy

Measured at a fixed ex-ante horizon, both outcome tokens scored, volume ≥ $30k,
slippage 0.01, bootstrap **clustered by event**, dead segments excluded:

| slice | n | events | win% | mean px | ROI | 95% CI | |
|---|---|---|---|---|---|---|---|
| 0.12–0.15 | 2,590 | 2,264 | 14.6% | 0.133 | +2.3% | [−7.5%, +11.5%] | **not significant** |
| 0.15–0.18 | 2,655 | 2,424 | 20.0% | 0.163 | +15.5% | [+7.4%, +24.1%] | |
| 0.18–0.21 | 2,766 | 2,539 | 24.6% | 0.193 | **+21.3%** | [+12.9%, +29.4%] | sweet spot |
| 0.21–0.24 | 3,087 | 2,835 | 27.8% | 0.223 | +19.0% | [+11.9%, +26.1%] | sweet spot |
| 0.24–0.27 | 3,391 | 3,128 | 29.7% | 0.253 | +12.9% | [+7.3%, +19.2%] | |
| 0.27–0.30 | 3,508 | 3,242 | 32.6% | 0.283 | +11.2% | [+6.3%, +16.7%] | band ceiling |
| 0.30–0.33 | 3,226 | 2,969 | 35.0% | 0.313 | +8.2% | [+2.8%, +13.0%] | significant but thin |
| 0.33–0.36 | 3,196 | 2,953 | 36.2% | 0.343 | +2.5% | [−2.3%, +6.9%] | **dead** |

Read it as a curve, not a band: edge switches on at 0.15, peaks around 0.18–0.24,
and decays to nothing by 0.33. The ceiling sits at 0.30 rather than 0.33 to keep a
margin of safety — 0.30–0.33's lower bound is only +2.8%.

Widening 0.25 → 0.30 trades ROI for sample: 0.15–0.25 scores +17.9% but on 7,473
events, while 0.15–0.30 scores +15.7% on 11,133. Flow, not ROI, is this book's
binding constraint, so the wider band wins on total expected profit.

Favorite-longshot bias, confirmed at scale: deep longshots (0.02–0.05) return
**−18.8%**, and everything ≥ 0.40 is reliably negative (−1.2% to −5.3%). Buying
favorites loses money.

## Sizing must follow the curve

Kelly takes a win rate, and for a long time that input was the flat constant
0.245 at every price. That is not a harmless simplification — **it inverts the
sizing.** With q fixed, f = q − (1−q)·p/(1−p) *falls* as p rises and goes negative
above p = 0.245, so the bot staked most at 0.15 (weakest measured edge, +15.5%)
and refused to trade above 0.245 at all — discarding the entire 0.245–0.30 range
where the edge is real.

Sizing now interpolates the measured win rate from the table above
(`backtest.live.calibrated_win_rate`). Full-Kelly then runs 0.031 → 0.056 → 0.067
→ 0.070 → 0.060 across 0.15 → 0.22 → 0.30, peaking where the edge peaks.

| price | old stake ($150 bankroll) | new stake ($1,000, ¼-Kelly) |
|---|---|---|
| 0.15 | $4.19 | $7.82 |
| 0.20 | $2.11 | $16.71 |
| 0.22 | $1.20 | $17.56 |
| 0.25 | **skipped** | $15.03 |
| 0.30 | **skipped** | $14.20 |

Kelly asking for less than the $1 minimum ticket now means **no bet**, not a
rounded-up $1 — rounding up handed the least attractive prices the same ticket as
the best ones.

## Segments: two of them have no edge

Measured at 0.15–0.30, 48h, event-clustered:

| segment | n | events | ROI | |
|---|---|---|---|---|
| other | 7,720 | 6,070 | +22.5% | [+18.2%, +26.7%] **EDGE** |
| sports-game | 4,591 | 3,158 | +6.5% | [+1.5%, +11.7%] **EDGE** |
| crypto-price | 2,296 | 1,364 | +11.6% | [+4.5%, +18.8%] **EDGE** |
| geopolitics | 230 | 162 | +34.0% | [+2.7%, +62.2%] **EDGE** |
| election | 317 | 214 | +9.1% | not significant |
| price-barrier | 135 | 103 | +5.1% | not significant |
| **mention-count** | 634 | 264 | **−3.7%** | negative at 24h (−1%), 48h (−4%), 96h (−5%); 2024 −19%, 2025 −6% |
| **fed-macro** | 43 | 30 | **−17.3%** | negative at every horizon (−34% / −17% / −60%) |

`mention-count` (tweet/mention counts) and `fed-macro` are both markets on a
**mechanical, publicly-tracked quantity** — a running post count, a rate decision
priced off fed-funds futures. The distribution is already well calibrated, so
there is no favourite-longshot bias to harvest. Excluding both lifts band ROI from
+14.8% to +15.7% and, more importantly, stops the book concentrating in them: the
live book had held 6 Elon tweet-count buckets and 4 legs of a single Fed decision.

This is not label-fishing. These were the two segments the book was most
concentrated in and the two this document already flagged as unproven.

## How to judge results — read this before calling the strategy broken

**Count settled *events*, not settled bets.** The single biggest inference error
made here: 38 paper bets looked like 38 observations but spanned only 13
independent events (8 Iran legs, 6 Elon tweet buckets, 4 BTC). At −50% realized
that looked catastrophic; tested properly, P(≤3 wins | edge is real) = **59.6%** —
entirely consistent with the edge existing.

Two guards now enforce this at the point of trading:
- one open bet per `event` key, held **across** cycles (`PaperStore.has_open_event`)
- ≤25% of bankroll resolving on any single date

**Negative skew means long losing runs are normal.** At a ~27% win rate, 10
straight losses has probability 0.73¹⁰ ≈ **4.3%** — it will happen. Judge on
realized ROI over dozens of settled *events*, not on a streak.

**Sample size needed.** To distinguish +16% from 0 at this variance takes roughly
100+ settled events. Below ~30, the honest answer to "is it working?" is "not yet
knowable."

**Check that settlement is actually running before reading any P&L.** See below —
a stale cache once held 16 resolved bets open for days and reported the book as
0W/17L when three of those bets had already won.

## Known open questions

- **2024 is negative** for both bands on a thin sample (~500 obs). The edge may
  be a post-2024 phenomenon, or that sample may just be too small.
- **The $10k–$30k volume tier is unmeasured.** `resolved_deep` holds 141,071
  markets in that range, but `bigtest fetch` only priced the ≥$30k ones, so a
  min-volume sweep below $30k returns identical numbers — that is missing data,
  not evidence of no effect. Pricing that tier is the biggest remaining flow
  lever and needs a `bigtest fetch --min-volume 10000` run. At the other end,
  ≥$100k scores **+18.1%** [+14.0%, +22.7%] on half the flow, so edge does not
  appear to *require* the largest markets.
- **Resolved 2026-08-01, re-measured 2026-08-03:** the hold window was tested
  directly on the full universe. Entering a market with H hours left and holding
  to resolution *is* an H-hour hold, so the horizon sweep is a hold-period
  experiment. Band 0.15–0.30, dead segments excluded, event-clustered:

  | hours | 6 | 24 | 48 | 72 | 96 | 120 | 168 |
  |---|---|---|---|---|---|---|---|
  | ROI | +14.7% | +16.5% | +15.7% | +15.7% | +15.6% | +13.9% | +12.5% |

  **Every point is significantly positive.** ROI is flat to 96h and gives up 2–3
  points out to 168h, so the window is set by FLOW, not edge. Two earlier readings
  on partial data were both noise and are retracted: "short horizons are worse"
  (19% subset) and "96h is a weak tail" (59% subset).
- **Resolved 2026-08-03: segment coverage.** The old worry — that `crypto-price`
  (+2.1%) and `price-barrier` (−3.8%) were unproven — was an artefact of measuring
  at the *old* 0.10–0.20 band. At 0.15–0.30 `crypto-price` is a significant
  **+11.6%** [+4.5%, +18.8%]. The segments that genuinely lack edge are
  `mention-count` and `fed-macro`, and both are now excluded.

## Flow is a real constraint

Edge is worthless if the scanner finds nothing. The time window, not the price
band, is the dominant filter. Measured live 2026-08-03, 2,100 liquid markets:

| window | in-window | tradeable events |
|---|---|---|
| 6–96h | 38 | 2 |
| 6–120h | 38 | 2 |
| **6–168h** | **65** | **6** |

At 6–96h the book was opening roughly one bet a day and sitting on 4% of its
capital. The 168h ceiling triples tradeable events for 2–3 points of ROI on the
marginal bet — a trade worth making while the sample is the scarce resource.

Watch this alongside ROI: `grep paper_cycle_done logs/cycle.log | tail`. Sustained
`opened=0` with a book below the exposure cap means the filters are too tight, not
that the edge is gone.

## Settlement must be verified, not assumed

On 2026-08-03 the book read **0W / 17L, ROI −100%** — and it was wrong. `DataFeed`
cached "this market is still open" for **3 days**, while the strategy only ever
holds markets 6–96h. Every bet's market was therefore inside the TTL window when
the settle loop asked about it, so the loop kept being told "not resolved yet".
Sixteen already-resolved bets sat open, freezing both their stake and their event
slot, and **hiding 3 wins**. Real backlog P&L was −1.7%, not −100%.

Fixed in two places: the TTL is now 1 hour, and `_settle` passes `refresh=True`
for any bet past its `resolves_at`, so a stale "still open" can never be believed
once the clock has run out. `tests/test_paper.py` guards both.

The general lesson: **a metric that can only move in one direction is a bug
until proven otherwise.** A 0% win rate over 17 bets was treated as a strategy
result for three days when it was a plumbing failure.

## Reproducing

```bash
python -m backtest.universe            # build resolved_deep via Gamma keyset
python -m backtest.bigtest fetch       # price every token at each horizon
python -m backtest.bigtest report      # band curve + segments + by-year
python -m paper.run review             # grade the live book against this file
```

Every number in this document comes from `backtest.bigtest.collect` +
`bootstrap_ci` (event-clustered) at horizon 48h, volume ≥ $30k, slippage 0.01,
unless stated otherwise.
