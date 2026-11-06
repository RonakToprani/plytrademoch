# Poly underdog paper state — 2026-11-06T11:03:49.503590+00:00

**Strategy:** buy the underdog outcome token priced **0.15–0.33** on liquid
Polymarket markets resolving in **6–168h**; hold to resolution. Fractional-
Kelly sizing (against a price-calibrated win rate) on a $1,000 paper bankroll.
NEGATIVE SKEW (~29.6% win rate) — judge on realized ROI over dozens of settled
EVENTS, not bets and not the first few.

**Read `EXPECTATIONS.md` in this repo before grading these results.** It is the
source of truth for what 'working' looks like, recalibrated 2026-08-05 on
355,896 markets / 218,734 events. Key points a reviewer must not get wrong:

- Expect **~+20.3% ROI** (95% CI [+16.8%, +24.0%]) and a **~29.6% win rate**
  on the GATED universe (game-winner / election / price-barrier / token-launch
  excluded alongside mention-count / fed-macro). Older figures (+50–70% from
  n=126, +15.7% from the ungated blend) are RETIRED — the ungated blend was
  carried by segments the scanner no longer buys.
- **Count settled EVENTS, not bets.** Correlated legs are not independent
  observations: 38 early paper bets spanned only 13 events, and a -50% result
  that looked catastrophic was P=59.6% under a real edge. Bets now carry an
  `event` key and only one open bet per event is allowed.
- **Losing streaks are expected.** At ~28% win, 10 straight losses has
  probability ~4.3%. Distinguishing +20% from 0 needs ~100+ settled events;
  below ~30 the honest answer is 'not yet knowable'.
- **Results before 2026-08-06 graded a different strategy.** Until 2026-08-05
  the scanner bought game-WINNER markets (MLB/tennis/esports/cricket dailies)
  — measured -0.8% n.s. at realistic spread — which made up ~85% of flow.
  Those are now excluded; only settled events opened on/after 2026-08-06
  test the gated strategy. (Bets before 2026-08-04 are doubly contaminated:
  sub-floor fills plus a stale resolution cache, both fixed 2026-08-03.)

## Book
- open **17** ($293.92)  ·  settled **487** (116W / 371L)
- realized P&L **$87.72**  ·  ROI **+1.2%** (backtest exp ~+20.3%)  ·  win **24%** (exp ~29.6%)
- last scan: 2026-11-06T10:47:19.230088+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| Will Elif Eralp be the next Governing Mayor of Berli | No | 0.304 | $16.52 | 2026-09-20T23:59:07.655567+00:00 |
| Will David Eby be the next Premier of British Columb | Yes | 0.230 | $21.08 | 2026-10-24T23:59:08.008167+00:00 |
| Military action against Saudi Oil Pipeline (East-Wes | Yes | 0.330 | $15.89 | 2026-10-31T20:59:06.774849+00:00 |
| US x Iran ceasefire continues through October 31? | No | 0.160 | $14.59 | 2026-10-31T23:59:10.580635+00:00 |
| Israel military action against Syria by October 31,  | Yes | 0.284 | $15.55 | 2026-10-31T20:59:09.925765+00:00 |
| Will Republicans lose the Alaska, Iowa, Kansas, Main | Yes | 0.260 | $18.61 | 2026-11-03T23:59:09.836803+00:00 |
| Israel x Iran ceasefire continues through November 7 | No | 0.180 | $15.88 | 2026-11-08T04:59:07.582186+00:00 |
| Game Handicap: T1 (-2.5) vs Karmine Corp (+2.5) | T1 | 0.310 | $16.47 | 2026-11-07T04:00:09.982302+00:00 |
| Will Al Qadisiyah Saudi Club vs. Al Fayha Saudi Club | No | 0.313 | $19.00 | 2026-11-05T17:30:10.933265+00:00 |
| Will Al Ettifaq Saudi Club vs. Al Hilal Saudi Club e | No | 0.300 | $17.22 | 2026-11-07T14:30:11.751533+00:00 |
| Will Al Ahli Saudi Club vs. Al Taawoun Saudi Club en | No | 0.299 | $19.43 | 2026-11-07T17:30:10.331228+00:00 |
| Will Ethereum reach $2,600 November 2-8? | Yes | 0.246 | $20.83 | 2026-11-09T05:00:11.929148+00:00 |
| Will Bitcoin reach $84,000 November 2-8? | Yes | 0.252 | $18.74 | 2026-11-09T05:00:10.500092+00:00 |
| US x Iran effective ceasefire continues through Nove | No | 0.190 | $16.53 | 2026-11-09T04:59:11.884677+00:00 |
| Will the price of Bitcoin be above $78,000 on Novemb | Yes | 0.250 | $17.22 | 2026-11-06T17:00:11.470679+00:00 |
| Will the price of Ethereum be above $2,300 on Novemb | Yes | 0.220 | $19.43 | 2026-11-06T17:00:11.047863+00:00 |
| Exact Score: Any Other Score? | Yes | 0.297 | $10.93 | 2026-11-07T15:00:07.086058+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
| Game Handicap: DK (-1.5) vs Bilibili Gaming (+1.5) | LOST | -18.61 |
| Will the price of Bitcoin be above $82,000 on Novemb | LOST | -11.06 |
| Will the price of Ethereum be above $2,400 on Novemb | WON | +44.92 |
| Map Handicap: FAL (-1.5) vs Natus Vincere (+1.5) | LOST | -17.22 |
| Will the price of Bitcoin be above $78,000 on Novemb | WON | +59.71 |
| Spread: Paris Saint-Germain FC (-1.5) | WON | +27.23 |
| Will the price of Bitcoin be above $76,000 on Novemb | LOST | -19.43 |
| Will Bitcoin dip to $76,000 on November 2? | LOST | -18.47 |
| Map Handicap: FAL (-1.5) vs Natus Vincere (+1.5) | LOST | -16.52 |
| Will the price of Ethereum be above $2,400 on Novemb | LOST | -18.95 |
| Will the price of Ethereum be above $2,300 on Novemb | LOST | -21.08 |
| Will Charles Leclerc win the 2026 F1 Mexican Grand P | LOST | -19.00 |
| Bitcoin Up or Down on November 1? | LOST | -19.00 |
| Ethereum Up or Down on November 1? | LOST | -17.20 |
| Will the price of Ethereum be above $2,300 on Novemb | LOST | -12.62 |
| Spread: Commanders (-17.5) | LOST | -15.88 |
| Spread: Rams (-14.5) | WON | +58.29 |
| Will Bitcoin dip to $76,000 on October 30? | LOST | -15.88 |
| Will the price of Bitcoin be above $76,000 on Octobe | LOST | -18.44 |
| Will Ethereum dip to $2,100 October 26-November 1? | LOST | -20.10 |
| Will Ethereum dip to $2,000 in October? | LOST | -10.93 |
| Will Bitcoin reach $82,000 October 26-November 1? | LOST | -20.42 |
| Will Vivek Ramaswamy pull the Amy Acton mother ad? | WON | +55.86 |
| Will Bitcoin dip to $78,000 on October 29? | WON | +47.35 |
| Will the price of Bitcoin be above $78,000 on Octobe | WON | +74.98 |
| Will Solana dip to $90 in October? | LOST | -18.47 |
| Will the price of Ethereum be above $2,400 on Octobe | LOST | -17.20 |
| Will Vitality Win the PGL Masters Bucharest 2026? | LOST | -21.08 |
| Will Bitcoin dip to $78,000 October 26-November 1? | WON | +37.13 |
| Will the price of Bitcoin be above $82,000 on Octobe | LOST | -16.52 |
| Will the price of Ethereum be above $2,400 on Octobe | LOST | -17.20 |
| Will Trump speak to Ahmed al-Sharaa by October 31? | LOST | -10.93 |
| 2026 Balance of Power: R Senate, D House | LOST | -17.92 |
| Will Trump endorse John Cornyn for TX-Sen by Nov 2 2 | LOST | -15.49 |
| Will commitments to the 1W public sale exceed $60M? | WON | +63.77 |
| Will Moonshot have the best Chinese AI model at the  | LOST | -16.53 |
| Will Paris Saint-Germain FC vs. Olympique Lyonnais e | LOST | -14.59 |
| Spread: Cowboys (-10.5) | WON | +36.66 |
| Next Astra Model (6.1+) released by October 31, 2026 | LOST | -12.23 |
| Will Google have the best AI model at the end of Oct | LOST | -11.32 |
| Will Kimi Antonelli win the 2026 F1 United States Gr | LOST | -17.20 |
| Will NVIDIA be the largest company in the world by m | WON | +45.78 |
| Will María Corina Machado enter Venezuela by October | WON | +80.92 |
| Will there be no next Fable model (5.2+) release by  | LOST | -14.16 |
| Next Fable Model (5.2+) released by October 31, 2026 | LOST | -14.66 |
| Bitcoin Up or Down on October 25? | LOST | -19.00 |
| FC Barcelona vs. Real Madrid CF: Both Teams to Score | LOST | -18.61 |
| Game Handicap: GEN (-1.5) vs LYON (+1.5) | WON | +33.77 |
| US-Iran ceasefire continues through the midterms? | WON | +73.09 |
| Spread: Saints (-3.5) | LOST | -16.58 |
| Spread: Seahawks (-7.5) | WON | +48.45 |
| Will Ethereum dip to $2,200 in October? | WON | +38.69 |
| Will Bitcoin reach $85,000 in October? | LOST | -16.52 |
| Will the Rhine River return to normal levels between | WON | +56.99 |
| Spread: Ravens (-3.5) | LOST | -16.58 |
| Spread: Panthers (-7.5) | LOST | -16.68 |
| Spread: Lions (-10.5) | LOST | -18.61 |
| Will Ethereum dip to $2,200 October 19-25? | LOST | -20.43 |
| Will FC Barcelona vs. Real Madrid CF end in a draw? | LOST | -12.23 |
| Will Bitcoin dip to $78,000 October 19-25? | LOST | -16.45 |

## Edge by price band (out-of-sample, cached universe, 48h horizon)
| band | n | win% | mean px | buy ROI |
|---|---|---|---|---|
| 0.02–0.10 | 9443 | 7% | 0.050 | +13% |
| 0.12–0.15 | 1793 | 16% | 0.133 | +13% |
| 0.15–0.20 | 2810 | 23% | 0.173 | +26% |
| 0.15–0.25 | 5730 | 26% | 0.199 | +24% |
| 0.15–0.30 | 8954 | 28% | 0.225 | +21% |
| 0.15–0.33 | 10371 | 30% | 0.237 | +20% |
| 0.20–0.33 | 7561 | 32% | 0.261 | +18% |
| 0.30–0.33 | 1417 | 37% | 0.313 | +14% |
| 0.33–0.36 | 1267 | 37% | 0.342 | +6% |
| 0.36–0.40 | 1635 | 39% | 0.378 | +1% |
| 0.80–0.90 | 5854 | 80% | 0.850 | -7% |
| 0.90–0.98 | 9564 | 93% | 0.948 | -3% |

## Paper results by entry price
| bucket | n | win% | ROI |
|---|---|---|---|
| <0.15 | 17 | 6% | -54% |
| 0.15–0.20 | 129 | 13% | -17% |
| 0.20–0.25 | 117 | 27% | +21% |
| 0.25–0.30 | 127 | 24% | -7% |
| 0.30–0.33 | 97 | 36% | +11% |
