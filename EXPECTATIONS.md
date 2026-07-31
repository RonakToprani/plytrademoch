# Strategy expectations — what "working" looks like

Last recalibrated **2026-07-31** on 355,896 resolved markets / 218,734 events.
Anything grading this strategy — the nightly review, the scheduled cloud
reviewer, or a human looking at the dashboard — should use the numbers here.

## The numbers

| Quantity | Expect | Notes |
|---|---|---|
| Entry band | **0.15 – 0.25** | was 0.10–0.20 until 2026-07-31 |
| Win rate | **~24.5%** | *not* 27% |
| ROI per bet | **~+17%** | 95% CI [+12.6%, +20.8%] |
| Hold window | 24–96h | unchanged; ROI is flat across lead times |
| Kelly input | 0.245 win rate, 0.25 multiple | sizing only; go/no-go is price-in-band |

**The old "+50–70% ROI, ~27% win rate" figures are retired.** They came from a
126-observation sample and were never precise enough to support that confidence.
Grading against them marks a perfectly on-spec strategy as "UNDERPERFORMING".

## Why the band moved

Measured at a fixed ex-ante horizon, both outcome tokens scored, volume ≥ $30k,
slippage 0.01, bootstrap **clustered by event**:

| band | n | events | win% | ROI | 95% CI | |
|---|---|---|---|---|---|---|
| 0.10–0.15 | 4,747 | 3,718 | 14.0% | +5.9% | [−1.6%, +13.5%] | **not significant** |
| 0.10–0.20 | 9,519 | 6,723 | 17.8% | +11.9% | [+6.9%, +17.0%] | old config |
| 0.15–0.20 | 4,772 | 4,103 | 21.6% | +17.8% | [+11.3%, +24.3%] | |
| **0.15–0.25** | **10,096** | **7,718** | **24.5%** | **+16.7%** | **[+12.6%, +20.8%]** | **current** |
| 0.20–0.30 | 11,311 | 8,936 | 29.5% | +13.6% | [+10.4%, +16.9%] | |

The bottom half of the old band carried no edge. Stable out-of-sample by year —
0.15–0.25 beat 0.10–0.20 in 2024 (−3.4% vs −17.8%), 2025 (+14.7% vs +12.9%) and
2026 (+20.3% vs +14.8%), and was independently significant in 2025 and 2026.

Favorite-longshot bias, confirmed at scale: deep longshots (0.02–0.05) return
**−18.8%**, and everything ≥ 0.40 is reliably negative (−1.2% to −5.3%). Buying
favorites loses money.

## How to judge results — read this before calling the strategy broken

**Count settled *events*, not settled bets.** The single biggest inference error
made here: 38 paper bets looked like 38 observations but spanned only 13
independent events (8 Iran legs, 6 Elon tweet buckets, 4 BTC). At −50% realized
that looked catastrophic; tested properly, P(≤3 wins | edge is real) = **59.6%** —
entirely consistent with the edge existing.

Two guards now enforce this at the point of trading:
- one open bet per `event` key, held **across** cycles (`PaperStore.has_open_event`)
- ≤25% of bankroll resolving on any single date

**Negative skew means long losing runs are normal.** At a ~24.5% win rate, 10
straight losses has probability 0.755¹⁰ ≈ **6.4%** — it will happen. Judge on
realized ROI over dozens of settled *events*, not on a streak.

**Sample size needed.** To distinguish +17% from 0 at this variance takes roughly
100+ settled events. Below ~30, the honest answer to "is it working?" is "not yet
knowable."

## Known open questions

- **Segment coverage.** Only "other" is individually significant (+26.8%). The
  segments the live bot most often buys — `crypto-price` (+2.1%) and
  `price-barrier` (−3.8%) — are **not significant** on their own. Whether the
  edge actually exists in the markets we trade is unresolved.
- **2024 is negative** for both bands on a thin sample (~500 obs). The edge may
  be a post-2024 phenomenon, or that sample may just be too small.
- Horizons here are measurement *lead times*, not a direct hold-period
  experiment. Changing the hold window needs its own test.

## Reproducing

```bash
python -m backtest.universe            # build resolved_deep via Gamma keyset
python -m backtest.bigtest fetch       # price every token at each horizon
python -m backtest.bigtest report      # band curve + segments + by-year
```
