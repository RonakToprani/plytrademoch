# Poly underdog paper state — 2026-09-03T10:58:17.576439+00:00

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
- open **9** ($152.80)  ·  settled **220** (50W / 170L)
- realized P&L **$49.34**  ·  ROI **+1.7%** (backtest exp ~+20.3%)  ·  win **23%** (exp ~29.6%)
- last scan: 2026-09-03T10:42:40.211902+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| 0 ships transit Hormuz on any date by August 31? | Yes | 0.213 | $18.52 | 2026-09-01T03:59:20.367108+00:00 |
| Icelandic European Union membership negotiations ref | Yes | 0.320 | $15.89 | 2026-08-30T03:59:07.639285+00:00 |
| Will Grand Theft Auto VI Extended Look get less than | No | 0.310 | $16.58 | 2026-09-03T23:59:07.385933+00:00 |
| Will Iran target Qatar by August 31, 2026? | Yes | 0.289 | $16.69 | 2026-08-31T20:59:07.657102+00:00 |
| Will Bitcoin dip to $74,000 August 31-September 6? | Yes | 0.290 | $15.89 | 2026-09-07T04:00:07.523710+00:00 |
| Will the price of Bitcoin be above $76,000 on Septem | No | 0.159 | $12.23 | 2026-09-03T16:00:07.430436+00:00 |
| 1st Half Spread: Real Sociedad de Fútbol (-1.5) | Real Sociedad de Fútbol | 0.260 | $19.85 | 2026-09-03T19:00:07.987475+00:00 |
| 1st Half Spread: Lille OSC (-1.5) | Lille OSC | 0.312 | $17.22 | 2026-09-03T18:45:08.737166+00:00 |
| Will OpenAI’s Astra model be released by September 3 | No | 0.220 | $19.93 | 2026-09-03T23:59:07.585946+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
| Bitcoin Up or Down on September 2? | LOST | -16.47 |
| Will the price of Bitcoin be above $76,000 on Septem | LOST | -17.20 |
| Next Mythos-Class Model released by September 1, 202 | WON | +33.45 |
| Seattle Mariners vs. Boston Red Sox: O/U 8.5 | WON | +33.59 |
| Bitcoin Up or Down on September 1? | WON | +40.84 |
| Will the price of Bitcoin be above $78,000 on Septem | WON | +69.20 |
| Game Handicap: GEN (-1.5) vs KT Rolster (+1.5) | LOST | -16.47 |
| Map Handicap: FAL (-1.5) vs MOUZ (+1.5) | LOST | -17.22 |
| Bitcoin Up or Down on August 31? | LOST | -19.93 |
| Will the price of Bitcoin be above $76,000 on August | LOST | -12.23 |
| Bitcoin Up or Down on August 30? | LOST | -15.89 |
| Google Maps renames Lake Ontario to "Lake America" b | WON | +26.96 |
| Will the price of Bitcoin be above $78,000 on August | LOST | -20.26 |
| Spread: Coventry City FC (-1.5) | LOST | -16.47 |
| Will Bitcoin reach $82,000 August 24-30? | LOST | -16.58 |
| Bitcoin Up or Down on August 28? | LOST | -13.41 |
| Will the price of Bitcoin be above $82,000 on August | LOST | -21.08 |
| Israel x Lebanon diplomatic meeting by August 31, 20 | LOST | -17.33 |
| Map Handicap: FAL (-1.5) vs Lynn Vision (+1.5) | WON | +27.23 |
| Another GTA VI trailer released by August 31? | LOST | -15.89 |
| Will Enzo Fernandez stay at Chelsea? | LOST | -14.59 |
| Bitcoin Up or Down on August 26? | LOST | -19.43 |
| Will Julian Alvarez stay at Atletico Madrid? | LOST | -16.57 |
| Will Maxx Crosby play for Dallas Cowboys next? | LOST | -17.33 |
| Next Mythos-Class Model released by August 31, 2026? | LOST | -17.22 |
| Iran-Oman Hormuz Agreement by August 31? | LOST | -12.23 |
| Will the price of Bitcoin be above $78,000 on August | LOST | -20.38 |
| Will Ethereum reach $2,800 in August? | LOST | -19.34 |
| Will XRP reach $1.80 in August? | LOST | -17.87 |
| Will Solana reach $120 in August? | LOST | -19.04 |
| Will Bitcoin reach $82,500 in August? | WON | +37.71 |
| Bitcoin Up or Down on August 25? | LOST | -14.59 |
| Will the total domestic gross for The Odyssey be at  | LOST | -21.03 |
| Will the total domestic gross for Spider-Man: Brand  | LOST | -11.32 |
| Will Fulham FC vs. Chelsea FC end in a draw? | LOST | -18.61 |
| Will Russia capture Kucheriv Yar by August 31? | LOST | -15.36 |
| Will Lando Norris win the 2026 F1 Dutch Grand Prix? | WON | +68.26 |
| Bitcoin Up or Down on August 23? | WON | +74.97 |
| Ethereum Up or Down on August 22? | LOST | -19.26 |
| Will Ethereum reach $2,600 August 17-23? | LOST | -18.01 |
| US ceasefire against Iran continues through August 3 | WON | +64.21 |
| Bitcoin Up or Down on August 22? | WON | +49.96 |
| Will Ethereum reach $2,500 August 17-23? | WON | +36.82 |
| Will Newcastle United FC vs. Liverpool FC end in a d | WON | +52.97 |
| Will Ethereum reach $2,400 August 17-23? | LOST | -16.68 |
| Bitcoin Up or Down on August 21? | LOST | -13.41 |
| Will the price of XRP be above $1.20 on August 21? | LOST | -18.28 |
| Will the price of Bitcoin be above $72,000 on August | LOST | -16.62 |
| Will Bitcoin reach $76,000 August 17-23? | WON | +65.78 |
| Will the price of Bitcoin be above $68,000 on August | LOST | -18.27 |
| Will the price of Ethereum be above $2,200 on August | LOST | -14.07 |
| Will the price of Ethereum be above $2,200 on August | LOST | -16.44 |
| Bitcoin Up or Down on August 20? | WON | +28.50 |
| Will the price of Bitcoin be above $70,000 on August | WON | +59.99 |
| Will Bitcoin reach $72,000 August 17-23? | WON | +70.13 |
| Will Bitcoin reach $66,000 August 17-23? | LOST | -16.47 |
| Iran-Oman Hormuz Agreement by August 22? | LOST | -10.93 |
| Will the price of Bitcoin be above $64,000 on August | LOST | -21.08 |
| Bitcoin Up or Down on August 19? | WON | +29.85 |
| Bitcoin Up or Down on August 18? | LOST | -17.92 |

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
| 0.15–0.20 | 62 | 16% | +18% |
| 0.20–0.25 | 55 | 24% | -8% |
| 0.25–0.30 | 49 | 24% | -4% |
| 0.30–0.33 | 37 | 38% | +15% |
