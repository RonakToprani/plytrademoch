# Poly underdog paper state — 2026-08-04T00:53:24.705604+00:00

**Strategy:** buy the underdog outcome token priced **0.15–0.30** on liquid
Polymarket markets resolving in **6–168h**; hold to resolution. Fractional-
Kelly sizing (against a price-calibrated win rate) on a $1,000 paper bankroll.
NEGATIVE SKEW (~27.4% win rate) — judge on realized ROI over dozens of settled
EVENTS, not bets and not the first few.

**Read `EXPECTATIONS.md` in this repo before grading these results.** It is the
source of truth for what 'working' looks like, recalibrated 2026-08-03 on
355,896 markets / 218,734 events. Key points a reviewer must not get wrong:

- Expect **~+15.7% ROI** (95% CI [+12.5%, +18.9%]) and a **~27.4% win rate**.
  The older '+50–70% ROI / ~27% win' figures came from n=126 and are RETIRED —
  grading against them marks an on-spec strategy as underperforming.
- **Count settled EVENTS, not bets.** Correlated legs are not independent
  observations: 38 early paper bets spanned only 13 events, and a -50% result
  that looked catastrophic was P=59.6% under a real edge. Bets now carry an
  `event` key and only one open bet per event is allowed.
- **Losing streaks are expected.** At ~27% win, 10 straight losses has
  probability ~4.3%. Distinguishing +16% from 0 needs ~100+ settled events;
  below ~30 the honest answer is 'not yet knowable'.
- **Results before 2026-08-03 are contaminated** and should not be read as a
  verdict on the strategy. Two defects, both now fixed: fills were allowed
  0.03 BELOW the band floor, into a slice measured at +2.3% (not significant),
  and those sub-floor bets account for essentially the entire realized loss
  (-$96 of -$101); and a 3-day resolution cache left resolved bets sitting
  open, so the book reported 0W/17L while 3 of those bets had already won.

## Book
- open **13** ($96.15)  ·  settled **44** (6W / 38L)
- realized P&L **$-100.67**  ·  ROI **-51.7%** (backtest exp ~+15.7%)  ·  win **14%** (exp ~27.4%)
- last scan: 2026-08-04T00:39:08.581594+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| 0 ships transit Hormuz on any date by July 31? | Yes | 0.136 | $6.91 | 2026-07-31T23:59:07.361878+00:00 |
| Israel x Iran ceasefire continues through August 2? | No | 0.110 | $7.08 | 2026-08-02T23:59:07.589500+00:00 |
| Will Donavan McKinney be the Democratic Nominee for  | No | 0.190 | $4.32 | 2026-08-04T00:00:07.524388+00:00 |
| Will Shri Thanedar be the Democratic Nominee for MI- | Yes | 0.190 | $3.91 | 2026-08-04T00:00:07.374051+00:00 |
| Will "Spider-Man: Brand New Day" Opening Weekend Box | No | 0.190 | $3.91 | 2026-08-02T23:59:06.069737+00:00 |
| Will Elon Musk post 280-299 tweets from July 28 to A | Yes | 0.182 | $2.91 | 2026-08-04T16:00:07.345902+00:00 |
| Will Spider-Man: Brand New Day beat Avengers: Endgam | No | 0.180 | $3.59 | 2026-08-02T23:59:07.372138+00:00 |
| Will the price of Bitcoin be above $62,000 on August | No | 0.190 | $3.99 | 2026-08-04T16:00:07.238505+00:00 |
| US announces end of Iranian blockade by August 7, 20 | Yes | 0.213 | $1.75 | 2026-08-07T23:59:07.628570+00:00 |
| Washington Nationals vs. Philadelphia Phillies | Philadelphia Phillies | 0.200 | $13.15 | 2026-08-10T22:40:04.615183+00:00 |
| Will Mike Lindell win the 2026 Minnesota Governor Re | No | 0.260 | $14.74 | 2026-08-11T00:00:05.318766+00:00 |
| Will Russell Fry be the new Republican nominee for S | Yes | 0.179 | $12.97 | 2026-08-11T00:00:06.077527+00:00 |
| Pittsburgh Pirates vs. Milwaukee Brewers | Milwaukee Brewers | 0.190 | $16.92 | 2026-08-10T23:40:06.835216+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
| Will Elon Musk post <40 tweets from August 1 to Augu | WON | +7.11 |
| LoL: LNG Esports vs Invictus Gaming (BO3) - LPL Grou | LOST | -2.33 |
| LoL: KT Rolster vs Hanwha Life Esports (BO3) - LCK R | WON | +3.17 |
| Bitcoin Up or Down on August 2? | LOST | -2.55 |
| Counter-Strike: Spirit vs MOUZ (BO5) - BLAST Bounty  | WON | +5.07 |
| UFC Fight Night: Daniel Rodriguez vs. Uroš Medic (We | LOST | -1.00 |
| UFC Fight Night: Jan Blachowicz vs. Navajo Stirling  | LOST | -1.00 |
| UFC Fight Night: Oban Elliott vs. Michael Oliveira ( | LOST | -1.00 |
| Will "Spider-Man: Brand New Day" score at least 90 o | LOST | -1.00 |
| UFC Fight Night: Marcin Tybura vs. Aleksandar Rakic  | LOST | -1.00 |
| Will Bitcoin reach $66,000 July 27-August 2? | LOST | -6.91 |
| Will Bitcoin dip to $62,000 July 27-August 2? | LOST | -3.91 |
| Will Elon Musk post 880-919 tweets in July 2026? | WON | +32.57 |
| Will Ethereum reach $2,000 in July? | LOST | -5.29 |
| Israel x Iran ceasefire continues through July 31? | LOST | -6.57 |
| Will Gold (XAUUSD) hit (LOW) $3,900 in July? | LOST | -6.27 |
| Will Apple be the second-largest company in the worl | WON | +14.80 |
| Will MrBeast's next video get less than 40 million v | LOST | -3.49 |
| Will Silver (XAGUSD) hit (LOW) $54 in July? | LOST | -4.12 |
| Will WTI Crude Oil (WTI) hit (LOW) $80 in July? | LOST | -4.32 |
| Will NVIDIA be the largest company in the world by m | WON | +13.96 |
| Will Bitcoin reach $67,500 in July? | LOST | -6.91 |
| Will S&P 500 (SPY) hit (HIGH) $760 in July? | LOST | -6.91 |
| Will WTI Crude Oil (WTI) hit (LOW) $75 in July? | LOST | -3.91 |
| Will Bitcoin dip to $60,000 in July? | LOST | -3.91 |
| US announces end of Iranian blockade by July 31, 202 | LOST | -5.48 |
| Will Russia capture Kostyantynivka by July 31? | LOST | -6.53 |
| Will Russia enter Serhiivka by July 31? | LOST | -6.88 |
| Will the Fed decide differently in the next three de | LOST | -4.42 |
| Will the Fed Pause–Pause–Pause in the next three dec | LOST | -4.56 |
| Will the Fed increase interest rates by 25 bps after | LOST | -4.54 |
| Will there be no change in Fed interest rates after  | LOST | -4.24 |
| Israel x Iran ceasefire continues through July 27? | LOST | -6.39 |
| Will Elon Musk post 260-279 tweets from July 21 to J | LOST | -3.62 |
| Will Elon Musk post 240-259 tweets from July 21 to J | LOST | -6.69 |
| Will Elon Musk post 340-359 tweets from July 21 to J | LOST | -6.86 |
| Will Elon Musk post 320-339 tweets from July 21 to J | LOST | -5.87 |
| Israel x Iran ceasefire continues through July 26? | LOST | -4.52 |
| Colorado Rockies vs. Milwaukee Brewers | LOST | -5.48 |
| Will Elon Musk post 300-319 tweets from July 21 to J | LOST | -6.43 |
| Iran full airspace closure by July 27? | LOST | -5.48 |
| Will Moonshot have the best Chinese AI model at the  | LOST | -5.80 |
| Will Alibaba have the best Chinese AI model at the e | LOST | -5.31 |
| Israel x Iran ceasefire continues through July 25? | LOST | -5.85 |

## Edge by price band (out-of-sample, cached universe, 48h horizon)
| band | n | win% | mean px | buy ROI |
|---|---|---|---|---|
| 0.02–0.10 | 11567 | 7% | 0.051 | +6% |
| 0.12–0.15 | 2590 | 15% | 0.133 | +2% |
| 0.15–0.20 | 4488 | 22% | 0.173 | +19% |
| 0.15–0.25 | 9608 | 25% | 0.200 | +18% |
| 0.15–0.30 | 15407 | 27% | 0.228 | +16% |
| 0.20–0.30 | 10919 | 30% | 0.250 | +14% |
| 0.30–0.33 | 3226 | 35% | 0.313 | +8% |
| 0.33–0.36 | 3196 | 36% | 0.343 | +3% |
| 0.80–0.90 | 8895 | 81% | 0.848 | -6% |
| 0.90–0.98 | 11761 | 93% | 0.947 | -3% |

## Paper results by entry price
| bucket | n | win% | ROI |
|---|---|---|---|
| <0.15 | 15 | 0% | -100% |
| 0.15–0.20 | 16 | 6% | -47% |
| 0.20–0.25 | 12 | 42% | +119% |
| 0.25–0.30 | 1 | 0% | -100% |
