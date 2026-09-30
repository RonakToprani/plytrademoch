# Poly underdog paper state — 2026-09-30T05:24:28.045948+00:00

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
- open **18** ($279.47)  ·  settled **322** (78W / 244L)
- realized P&L **$170.70**  ·  ROI **+3.7%** (backtest exp ~+20.3%)  ·  win **24%** (exp ~29.6%)
- last scan: 2026-09-30T05:00:36.436825+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| Will Elif Eralp be the next Governing Mayor of Berli | No | 0.304 | $16.52 | 2026-09-20T23:59:07.655567+00:00 |
| US announces end of Iranian blockade by September 30 | Yes | 0.160 | $14.59 | 2026-10-01T03:59:07.348144+00:00 |
| Will Anthropic have the best Code Arena | WebDev AI  | No | 0.200 | $15.88 | 2026-09-30T16:00:07.723560+00:00 |
| Will Bitcoin reach $90,000 in September? | Yes | 0.156 | $12.62 | 2026-10-01T04:00:07.584059+00:00 |
| Will Ethereum reach $2,900 in September? | Yes | 0.210 | $18.95 | 2026-10-01T04:00:08.368131+00:00 |
| Will Russia and Ukraine hold any diplomatic meeting  | Yes | 0.208 | $17.87 | 2026-10-01T03:59:19.832229+00:00 |
| Will Solana reach $130 in September? | Yes | 0.188 | $10.93 | 2026-10-01T04:00:20.511319+00:00 |
| Russia-Ukraine peace talks by September 30, 2026? | Yes | 0.209 | $19.24 | 2026-10-01T03:59:06.717925+00:00 |
| Will XRP reach $1.80 in September? | Yes | 0.174 | $12.36 | 2026-10-01T04:00:07.264410+00:00 |
| Saudi Oil Pipeline (East-West) restarts by September | Yes | 0.330 | $13.41 | 2026-10-01T03:59:07.341440+00:00 |
| Will Russia capture all of Chasiv Yar by September 3 | Yes | 0.210 | $15.88 | 2026-10-01T03:59:07.310100+00:00 |
| US-Iran Hormuz Agreement by September 30? | Yes | 0.176 | $13.94 | 2026-10-01T03:59:07.735123+00:00 |
| Will Xiaomi have the best Chinese AI model at the en | No | 0.260 | $19.98 | 2026-09-30T16:00:07.887662+00:00 |
| Will Russia enter Mykolaivka by September 30, 2026? | Yes | 0.308 | $16.63 | 2026-10-01T03:59:07.673339+00:00 |
| 0 ships transit Hormuz on any date by September 30? | Yes | 0.248 | $18.47 | 2026-10-01T03:59:08.177054+00:00 |
| Next US-Iran senior diplomatic meeting by September  | Yes | 0.323 | $17.22 | 2026-09-30T23:59:07.739044+00:00 |
| Iran charges Hormuz fees by September 30? | Yes | 0.167 | $12.10 | 2026-10-01T03:59:07.684360+00:00 |
| Gemini 4.0 released by September 30, 2026? | Yes | 0.182 | $12.88 | 2026-10-01T03:59:07.404560+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
| Chicago White Sox vs. Houston Astros: O/U 8.5 | LOST | -10.93 |
| Philadelphia Phillies vs. Atlanta Braves: O/U 6.5 | WON | +51.66 |
| Will Bitcoin dip to $81,000 on September 28? | LOST | -17.87 |
| Will the price of Bitcoin be above $82,000 on Septem | LOST | -15.55 |
| Spread: Bears (-3.5) | WON | +64.16 |
| Spread: Vikings (-7.5) | LOST | -17.92 |
| Will the price of Bitcoin be above $84,000 on Septem | LOST | -15.88 |
| Spread: Lions (-14.5) | LOST | -18.61 |
| Spread: 49ers (-14.5) | LOST | -16.58 |
| Spread: Bills (-14.5) | LOST | -17.22 |
| Spread: Giants (-7.5) | LOST | -16.68 |
| Spread: Raiders (-3.5) | WON | +52.97 |
| Spread: Chiefs (-3.5) | LOST | -18.61 |
| Will “Hate That I Made You Love Me” by Ariana Grande | LOST | -15.89 |
| Map Handicap: paiN (-1.5) vs Galorys (+1.5) | WON | +44.28 |
| Will George Russell win the 2026 F1 Azerbaijan Grand | LOST | -20.42 |
| Will England vs. Spain end in a draw? | LOST | -17.22 |
| Will the price of Bitcoin be above $84,000 on Septem | LOST | -21.08 |
| Bitcoin Up or Down on September 26? | LOST | -16.47 |
| Spread: Steelers (-3.5) | LOST | -17.22 |
| Spread: Colts (-3.5) | LOST | -13.41 |
| Spread: Broncos (-3.5) | WON | +33.77 |
| Spread: Cowboys (-3.5) | LOST | -18.61 |
| Will MrBeast's next video get between 70 and 80 mill | LOST | -16.63 |
| Map Handicap: KC (-1.5) vs XLG Gaming (+1.5) | LOST | -17.57 |
| Bitcoin Up or Down on September 25? | WON | +34.87 |
| Will the price of Bitcoin be above $82,000 on Septem | LOST | -19.51 |
| Bitcoin Up or Down on September 24? | WON | +65.05 |
| Will the price of Bitcoin be above $84,000 on Septem | WON | +63.63 |
| CNN, Politico, or MS NOW unbanned from White House b | LOST | -12.23 |
| Trump renames AI by September 30? | WON | +48.45 |
| Will Bitcoin reach $88,000 September 21-27? | WON | +28.50 |
| Will the next Claude Opus model be released on Septe | LOST | -19.93 |
| Will the price of Bitcoin be above $86,000 on Septem | WON | +71.84 |
| Will the price of Bitcoin be above $82,000 on Septem | WON | +40.57 |
| Will the price of Bitcoin be above $80,000 on Septem | LOST | -20.18 |
| US x Iran ceasefire continues through September 25? | LOST | -18.95 |
| Trump x Greenland deal signed by September 23? | LOST | -16.41 |
| Will Xi Jinping visit US by September 23? | LOST | -17.53 |
| Will Ethereum reach $2,700 September 14-20? | WON | +72.65 |
| Bitcoin Up or Down on September 19? | LOST | -20.42 |
| Spread: West Virginia (-0.5) | WON | +64.16 |
| Will Bitcoin reach $82,000 September 14-20? | LOST | -14.91 |
| Will Bologna FC 1909 vs. Torino FC end in a draw? | WON | +44.28 |
| Will the price of Bitcoin be above $80,000 on Septem | LOST | -19.21 |
| Will MrBeast Gaming's next video get between 40 and  | LOST | -11.06 |
| Saudi Oil Pipeline (East-West) restarts by September | LOST | -20.67 |
| Will the price of Bitcoin be above $78,000 on Septem | WON | +44.87 |
| Map Handicap: VIT (-1.5) vs magic (+1.5) | LOST | -16.47 |
| Bitcoin Up or Down on September 17? | LOST | -20.26 |
| Will Bitcoin reach $80,000 September 14-20? | WON | +49.32 |
| Bitcoin Up or Down on September 16? | LOST | -18.47 |
| Will the price of Bitcoin be above $74,000 on Septem | LOST | -16.21 |
| Will the price of Bitcoin be above $78,000 on Septem | LOST | -16.52 |
| Bitcoin Up or Down on September 14? | LOST | -21.08 |
| Will the price of Bitcoin be above $78,000 on Septem | WON | +27.23 |
| Will Kimi Antonelli win the 2026 F1 Spanish Grand Pr | WON | +73.09 |
| Will “The Late Show With Stephen Colbert” win Emmys  | LOST | -17.22 |
| Map Handicap: LGC (-1.5) vs G2 (+1.5) | WON | +36.66 |
| Spread: Arsenal FC (-1.5) | WON | +27.23 |

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
| 0.15–0.20 | 79 | 14% | -10% |
| 0.20–0.25 | 78 | 31% | +35% |
| 0.25–0.30 | 86 | 23% | -12% |
| 0.30–0.33 | 62 | 35% | +7% |
