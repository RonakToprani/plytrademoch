# Poly underdog paper state — 2026-10-18T13:24:12.579795+00:00

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
- open **11** ($189.13)  ·  settled **404** (95W / 309L)
- realized P&L **$-17.95**  ·  ROI **-0.3%** (backtest exp ~+20.3%)  ·  win **24%** (exp ~29.6%)
- last scan: 2026-10-18T13:02:04.634891+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| Will Elif Eralp be the next Governing Mayor of Berli | No | 0.304 | $16.52 | 2026-09-20T23:59:07.655567+00:00 |
| Saudi Arabia military action against Yemen on Octobe | No | 0.284 | $14.59 | 2026-10-09T03:59:07.205108+00:00 |
| US x Iran ceasefire continues through October 22? | No | 0.180 | $15.23 | 2026-10-23T03:59:07.623067+00:00 |
| Will Ethereum dip to $2,300 October 12-18? | Yes | 0.253 | $20.73 | 2026-10-19T04:00:07.525099+00:00 |
| Spread: Eagles (-3.5) | Eagles | 0.260 | $18.61 | 2026-10-18T17:00:07.672108+00:00 |
| Spread: Browns (-3.5) | Browns | 0.260 | $18.61 | 2026-10-18T17:00:08.363888+00:00 |
| Will David Eby be the next Premier of British Columb | Yes | 0.230 | $21.08 | 2026-10-24T23:59:08.008167+00:00 |
| Spread: Rams (-21.5) | Rams | 0.220 | $20.42 | 2026-10-18T20:05:07.402844+00:00 |
| Spread: Chiefs (-3.5) | Chargers | 0.330 | $13.41 | 2026-10-18T20:25:08.031688+00:00 |
| Next Fable Model (5.2+) released by October 24, 2026 | No | 0.330 | $13.41 | 2026-10-25T03:59:06.905616+00:00 |
| Will "Grand Theft Auto VI Launch Trailer" get betwee | Yes | 0.309 | $16.52 | 2026-10-23T03:59:06.680639+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
| Will the price of Bitcoin be above $82,000 on Octobe | LOST | -17.20 |
| Bitcoin Up or Down on October 17? | LOST | -14.66 |
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
| Spread: Cardinals (-3.5) | LOST | -19.43 |
| Spread: Chargers (-3.5) | LOST | -18.61 |
| Spread: Steelers (-7.5) | WON | +38.69 |
| Spread: Ravens (-3.5) | WON | +44.28 |
| Spread: 49ers (-3.5) | LOST | -17.22 |
| Will Ethereum dip to $2,400 October 5-11? | LOST | -20.68 |
| Map Handicap: MOUZ (-1.5) vs FURIA (+1.5) | WON | +33.77 |
| Map Handicap: TS (-1.5) vs Team Falcons (+1.5) | WON | +33.77 |
| Israel military action against Lebanon on October 15 | LOST | -10.93 |
| Will the price of Bitcoin be above $80,000 on Octobe | LOST | -20.37 |
| Will Jynxzi, Ron and Los beat the Minecraft challeng | WON | +37.34 |
| Will the price of Bitcoin be above $82,000 on Octobe | WON | +62.19 |
| Will Ethereum dip to $2,500 October 5-11? | WON | +52.97 |
| Map Handicap: FAL (-1.5) vs Natus Vincere (+1.5) | LOST | -15.89 |
| Will Bitcoin reach $92,000 October 5-11? | LOST | -18.47 |
| Bitcoin Up or Down on October 5? | LOST | -14.59 |
| Will the price of Bitcoin be above $88,000 on Octobe | LOST | -15.30 |
| Will Sudan's Emergency Response Rooms win the Nobel  | LOST | -12.23 |
| Game Handicap: KT (-1.5) vs RED Canids (+1.5) | LOST | -18.47 |
| Spread: Ravens (-3.5) | LOST | -18.61 |
| Spread: Raiders (-3.5) | LOST | -19.43 |
| Spread: Buccaneers (-3.5) | LOST | -17.22 |
| Spread: Colts (-10.5) | WON | +38.69 |
| Spread: Panthers (-3.5) | WON | +64.16 |
| Patriots vs. Bills: O/U 57.5 | LOST | -16.58 |
| San Diego Padres vs. Milwaukee Brewers: O/U 6.5 | WON | +58.12 |
| Spread: Vikings (-3.5) | LOST | -17.92 |
| Map Handicap: GLS (-1.5) vs Grêmio Esports (+1.5) | LOST | -13.41 |
| Will Argentina vs. Burkina Faso end in a draw? | LOST | -14.59 |
| Spread: Burkina Faso (-5.5) | LOST | -11.84 |
| Will Ethereum dip to $2,600 September 28-October 4? | LOST | -16.44 |
| Will the price of Bitcoin be above $84,000 on Octobe | LOST | -19.43 |
| Flávio Bolsonaro participates in debate before first | LOST | -12.88 |
| Will the price of Ethereum be above $2,800 on Octobe | LOST | -18.33 |
| Will Bitcoin reach $90,000 September 28-October 4? | LOST | -16.47 |
| Bitcoin Up or Down on October 2? | LOST | -18.61 |
| Will MrBeast Gaming's next video get between 30 and  | LOST | -15.88 |
| Will Russia target Kyiv on October 4, 2026? | LOST | -20.42 |
| Will the price of Bitcoin be above $82,000 on Octobe | LOST | -16.53 |
| Bitcoin Up or Down on October 1? | WON | +74.74 |
| Map Handicap: FaZe (-1.5) vs Nemiga (+1.5) | LOST | -16.47 |
| Will Wales vs. Norway end in a draw? | LOST | -18.47 |

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
| 0.15–0.20 | 104 | 12% | -22% |
| 0.20–0.25 | 98 | 28% | +21% |
| 0.25–0.30 | 104 | 24% | -8% |
| 0.30–0.33 | 81 | 36% | +10% |
