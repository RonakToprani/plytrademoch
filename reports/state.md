# Poly underdog paper state — 2026-10-31T02:47:38.785952+00:00

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
- open **30** ($482.05)  ·  settled **446** (108W / 338L)
- realized P&L **$194.40**  ·  ROI **+2.9%** (backtest exp ~+20.3%)  ·  win **24%** (exp ~29.6%)
- last scan: 2026-10-31T02:17:07.606664+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| Will Elif Eralp be the next Governing Mayor of Berli | No | 0.304 | $16.52 | 2026-09-20T23:59:07.655567+00:00 |
| Saudi Arabia military action against Yemen on Octobe | No | 0.284 | $14.59 | 2026-10-09T03:59:07.205108+00:00 |
| Will David Eby be the next Premier of British Columb | Yes | 0.230 | $21.08 | 2026-10-24T23:59:08.008167+00:00 |
| Israel x Iran ceasefire continues through October 31 | No | 0.200 | $18.47 | 2026-10-31T20:29:06.034190+00:00 |
| NATO x Russia military clash by October 31, 2026? | Yes | 0.160 | $10.93 | 2026-11-01T03:59:11.157267+00:00 |
| Iran full airspace closure by October 31, 2026? | Yes | 0.196 | $10.93 | 2026-11-01T03:59:10.963744+00:00 |
| Israeli airspace closed by October 31, 2026? | Yes | 0.181 | $14.59 | 2026-11-01T03:59:10.544839+00:00 |
| Will the Rhine River return to normal levels between | No | 0.270 | $21.08 | 2026-10-31T23:59:07.233784+00:00 |
| Military action against Saudi Oil Pipeline (East-Wes | Yes | 0.330 | $15.89 | 2026-10-31T20:59:06.774849+00:00 |
| Will Bitcoin reach $85,000 in October? | Yes | 0.310 | $16.52 | 2026-11-01T04:00:09.392544+00:00 |
| US-Iran ceasefire continues through the midterms? | No | 0.210 | $19.43 | 2026-11-04T04:59:06.574561+00:00 |
| Next Fable Model (5.2+) released by October 31, 2026 | Yes | 0.330 | $14.66 | 2026-10-31T23:59:06.452530+00:00 |
| Will there be no next Fable model (5.2+) release by  | No | 0.328 | $14.16 | 2026-11-01T03:59:11.717122+00:00 |
| Will NVIDIA be the largest company in the world by m | No | 0.275 | $17.32 | 2026-11-01T03:59:13.180275+00:00 |
| Will Google have the best AI model at the end of Oct | No | 0.162 | $11.32 | 2026-10-31T16:00:11.681580+00:00 |
| Next Astra Model (6.1+) released by October 31, 2026 | Yes | 0.166 | $12.23 | 2026-10-31T23:59:09.211806+00:00 |
| US x Iran ceasefire continues through October 31? | No | 0.160 | $14.59 | 2026-10-31T23:59:10.580635+00:00 |
| Israel military action against Syria by October 31,  | Yes | 0.284 | $15.55 | 2026-10-31T20:59:09.925765+00:00 |
| Will Moonshot have the best Chinese AI model at the  | Yes | 0.229 | $16.53 | 2026-10-31T16:00:10.422572+00:00 |
| Will Trump endorse John Cornyn for TX-Sen by Nov 2 2 | Yes | 0.295 | $15.49 | 2026-11-04T00:00:07.300725+00:00 |
| 2026 Balance of Power: R Senate, D House | Yes | 0.270 | $17.92 | 2026-11-04T04:59:10.141943+00:00 |
| Will Trump speak to Ahmed al-Sharaa by October 31? | Yes | 0.233 | $10.93 | 2026-11-01T03:59:09.010687+00:00 |
| Will Republicans lose the Alaska, Iowa, Kansas, Main | Yes | 0.260 | $18.61 | 2026-11-03T23:59:09.836803+00:00 |
| Will Solana dip to $90 in October? | Yes | 0.250 | $18.47 | 2026-11-01T04:00:07.237412+00:00 |
| Will Vivek Ramaswamy pull the Amy Acton mother ad? | Yes | 0.248 | $18.47 | 2026-11-01T03:59:10.230278+00:00 |
| Will Bitcoin reach $82,000 October 26-November 1? | Yes | 0.215 | $20.42 | 2026-11-02T05:00:08.850241+00:00 |
| Will Ethereum dip to $2,000 in October? | Yes | 0.157 | $10.93 | 2026-11-01T04:00:09.768086+00:00 |
| Will Ethereum dip to $2,100 October 26-November 1? | Yes | 0.256 | $20.10 | 2026-11-02T05:00:11.259220+00:00 |
| Will the price of Bitcoin be above $76,000 on Octobe | No | 0.260 | $18.44 | 2026-10-31T16:00:11.136441+00:00 |
| Will Bitcoin dip to $76,000 on October 30? | Yes | 0.173 | $15.88 | 2026-10-31T04:00:07.245133+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
| Will Bitcoin dip to $78,000 on October 29? | WON | +47.35 |
| Will the price of Bitcoin be above $78,000 on Octobe | WON | +74.98 |
| Will the price of Ethereum be above $2,400 on Octobe | LOST | -17.20 |
| Will Vitality Win the PGL Masters Bucharest 2026? | LOST | -21.08 |
| Will Bitcoin dip to $78,000 October 26-November 1? | WON | +37.13 |
| Will the price of Bitcoin be above $82,000 on Octobe | LOST | -16.52 |
| Will the price of Ethereum be above $2,400 on Octobe | LOST | -17.20 |
| Will commitments to the 1W public sale exceed $60M? | WON | +63.77 |
| Will Paris Saint-Germain FC vs. Olympique Lyonnais e | LOST | -14.59 |
| Spread: Cowboys (-10.5) | WON | +36.66 |
| Will Kimi Antonelli win the 2026 F1 United States Gr | LOST | -17.20 |
| Will María Corina Machado enter Venezuela by October | WON | +80.92 |
| Bitcoin Up or Down on October 25? | LOST | -19.00 |
| FC Barcelona vs. Real Madrid CF: Both Teams to Score | LOST | -18.61 |
| Game Handicap: GEN (-1.5) vs LYON (+1.5) | WON | +33.77 |
| Spread: Saints (-3.5) | LOST | -16.58 |
| Spread: Seahawks (-7.5) | WON | +48.45 |
| Will Ethereum dip to $2,200 in October? | WON | +38.69 |
| Spread: Ravens (-3.5) | LOST | -16.58 |
| Spread: Panthers (-7.5) | LOST | -16.68 |
| Spread: Lions (-10.5) | LOST | -18.61 |
| Will Ethereum dip to $2,200 October 19-25? | LOST | -20.43 |
| Will FC Barcelona vs. Real Madrid CF end in a draw? | LOST | -12.23 |
| Will Bitcoin dip to $78,000 October 19-25? | LOST | -16.45 |
| Will the price of Bitcoin be above $80,000 on Octobe | WON | +75.35 |
| Spread: Club Atlético de Madrid (-3.5) | LOST | -15.88 |
| Will the price of Bitcoin be above $80,000 on Octobe | LOST | -10.93 |
| Will the price of Bitcoin be above $82,000 on Octobe | WON | +71.63 |
| Will Bitcoin dip to $80,000 October 19-25? | WON | +70.07 |
| Will the Bank of Russia decrease the key rate after  | LOST | -20.93 |
| Will the Bank of Canada make no change to the target | LOST | -10.93 |
| Next Astra Model (6.1+) released by October 23, 2026 | LOST | -17.64 |
| Game Handicap: KC (-1.5) vs MVK Esports (+1.5) | LOST | -20.26 |
| Will Bitcoin dip to $80,000 October 12-18? | LOST | -14.59 |
| Will "Grand Theft Auto VI Launch Trailer" get betwee | LOST | -16.52 |
| Next Fable Model (5.2+) released by October 24, 2026 | WON | +27.23 |
| Spread: Chiefs (-3.5) | LOST | -13.41 |
| Spread: Rams (-21.5) | LOST | -20.42 |
| Spread: Browns (-3.5) | LOST | -18.61 |
| Spread: Eagles (-3.5) | LOST | -18.61 |
| Will Ethereum dip to $2,300 October 12-18? | LOST | -20.73 |
| Will the price of Bitcoin be above $82,000 on Octobe | LOST | -17.20 |
| Bitcoin Up or Down on October 17? | LOST | -14.66 |
| US x Iran ceasefire continues through October 22? | LOST | -15.23 |
| Game Handicap: C9 (-1.5) vs FURIA Esports (+1.5) | WON | +27.23 |
| Will Bitcoin dip to $81,000 on October 16? | WON | +82.53 |
| Game Handicap: KC (-1.5) vs MVK Esports (+1.5) | LOST | -16.58 |
| Will the price of Bitcoin be above $84,000 on Octobe | LOST | -12.10 |
| Will Bitcoin dip to $80,000 October 12-18? | LOST | -18.95 |
| Bitcoin Up or Down on October 15? | WON | +62.79 |
| Will the price of Bitcoin be above $80,000 on Octobe | LOST | -16.50 |
| Will Bitcoin dip to $80,000 on October 14? | LOST | -15.62 |
| Will the price of Bitcoin be above $82,000 on Octobe | LOST | -15.89 |
| Gemini 4.0 released by October 15, 2026? | LOST | -16.58 |
| Spread: Bills (-3.5) | LOST | -17.22 |
| Will Coventry City FC vs. Newcastle United FC end in | LOST | -17.92 |
| Los Angeles Dodgers vs. Milwaukee Brewers: O/U 6.5 | LOST | -14.59 |
| Game Handicap: KT (-1.5) vs Team Vitality (+1.5) | WON | +40.84 |
| Map Handicap: VIT (-2.5) vs MOUZ (+2.5) | WON | +73.09 |
| Will Max Verstappen win the 2026 F1 Singapore Grand  | LOST | -16.47 |

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
| 0.15–0.20 | 116 | 14% | -12% |
| 0.20–0.25 | 107 | 28% | +24% |
| 0.25–0.30 | 114 | 24% | -10% |
| 0.30–0.33 | 92 | 37% | +14% |
