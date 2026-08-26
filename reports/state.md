# Poly underdog paper state — 2026-08-26T23:00:16.669139+00:00

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
- open **14** ($229.23)  ·  settled **187** (42W / 145L)
- realized P&L **$134.48**  ·  ROI **+5.8%** (backtest exp ~+20.3%)  ·  win **22%** (exp ~29.6%)
- last scan: 2026-08-26T22:45:07.750493+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| US ceasefire against Iran continues through August 3 | No | 0.160 | $12.23 | 2026-08-31T23:59:07.722673+00:00 |
| Will Russia capture Kucheriv Yar by August 31? | Yes | 0.193 | $15.36 | 2026-09-01T03:59:06.961406+00:00 |
| Will the total domestic gross for Spider-Man: Brand  | Yes | 0.156 | $11.32 | 2026-08-31T23:59:07.538558+00:00 |
| Will the total domestic gross for The Odyssey be at  | Yes | 0.248 | $21.03 | 2026-08-31T23:59:08.248942+00:00 |
| Will Bitcoin reach $82,500 in August? | No | 0.305 | $16.58 | 2026-09-01T04:00:07.369956+00:00 |
| Will Solana reach $120 in August? | Yes | 0.194 | $19.04 | 2026-09-01T04:00:08.100223+00:00 |
| Will XRP reach $1.80 in August? | Yes | 0.209 | $17.87 | 2026-09-01T04:00:08.797578+00:00 |
| Will Ethereum reach $2,800 in August? | Yes | 0.224 | $19.34 | 2026-09-01T04:00:19.673291+00:00 |
| 0 ships transit Hormuz on any date by August 31? | Yes | 0.213 | $18.52 | 2026-09-01T03:59:20.367108+00:00 |
| Iran-Oman Hormuz Agreement by August 31? | Yes | 0.180 | $12.23 | 2026-09-01T03:59:07.880224+00:00 |
| Next Mythos-Class Model released by August 31, 2026? | Yes | 0.306 | $17.22 | 2026-08-31T03:59:07.155659+00:00 |
| Will Maxx Crosby play for Dallas Cowboys next? | Yes | 0.318 | $17.33 | 2026-09-01T00:00:07.271758+00:00 |
| Will Julian Alvarez stay at Atletico Madrid? | No | 0.300 | $16.57 | 2026-09-02T03:59:07.651956+00:00 |
| Will Enzo Fernandez stay at Chelsea? | Yes | 0.191 | $14.59 | 2026-09-02T03:59:07.611511+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
| Bitcoin Up or Down on August 26? | LOST | -19.43 |
| Will the price of Bitcoin be above $78,000 on August | LOST | -20.38 |
| Bitcoin Up or Down on August 25? | LOST | -14.59 |
| Will Fulham FC vs. Chelsea FC end in a draw? | LOST | -18.61 |
| Will Lando Norris win the 2026 F1 Dutch Grand Prix? | WON | +68.26 |
| Bitcoin Up or Down on August 23? | WON | +74.97 |
| Ethereum Up or Down on August 22? | LOST | -19.26 |
| Will Ethereum reach $2,600 August 17-23? | LOST | -18.01 |
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
| Game Handicap: KC (-1.5) vs GIANTX (+1.5) | LOST | -16.86 |
| Will the price of Bitcoin be above $64,000 on August | WON | +80.64 |
| Bitcoin Up or Down on August 17? | WON | +36.66 |
| Will Real Madrid win on 2026-08-16? | LOST | -16.86 |
| Will TSG Hoffenheim win on 2026-08-16? | LOST | -15.23 |
| Afghanistan Tour of Ireland ODIs: Ireland vs Afghani | LOST | -19.85 |
| Bitcoin Up or Down on August 15? | LOST | -20.26 |
| Bitcoin Up or Down on August 14? | LOST | -18.27 |
| Will Australia win? | LOST | -15.89 |
| US-Iran 60 day negotiation period extended? | LOST | -19.43 |
| Will Bitcoin reach $66,000 August 10-16? | LOST | -17.20 |
| Bitcoin Up or Down on August 13? | WON | +56.72 |
| Will MrBeast's next video get between 80 and 90 mill | LOST | -19.88 |
| ITF M25 Kursumlijska Banja 3 Men: George Lazarov vs  | LOST | -17.87 |
| Bitcoin Up or Down on August 12? | WON | +27.23 |
| Will Deportivo Toluca FC win on 2026-08-12? | LOST | -13.41 |
| US announces end of Iranian blockade by August 15, 2 | LOST | -14.59 |
| Will FC Cincinnati win on 2026-08-11? | WON | +38.69 |
| Will the price of Bitcoin be above $64,000 on August | WON | +52.97 |
| Will Kai and Speed beat the Minecraft challenge by A | WON | +59.71 |
| Spread: St. Louis Cardinals (-1.5) | LOST | -16.58 |
| Game Handicap: RED (-1.5) vs Leviatan Esports (+1.5) | WON | +32.26 |
| Bitcoin Up or Down on August 10? | LOST | -13.41 |
| Game Handicap: G2 (-1.5) vs Team Heretics (+1.5) | LOST | -16.68 |
| Will the next Google Gemini Pro model be released by | LOST | -12.23 |
| Bitcoin Up or Down on August 9? | WON | +73.09 |
| Iran-Oman Hormuz Agreement by August 15? | WON | +47.64 |
| US-Iran Hormuz Agreement by August 15? | LOST | -18.47 |
| Will Independiente Santa Fe win on 2026-08-09? | LOST | -19.43 |
| Bitcoin Up or Down on August 8? | LOST | -13.41 |
| US announces end of Iranian blockade by August 9, 20 | LOST | -20.42 |
| Will Marcelo attend Cristiano Ronaldo's wedding? | LOST | -19.00 |
| Will the price of Bitcoin be above $64,000 on August | LOST | -17.22 |

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
| 0.15–0.20 | 55 | 16% | +25% |
| 0.20–0.25 | 47 | 26% | +1% |
| 0.25–0.30 | 45 | 24% | -3% |
| 0.30–0.33 | 23 | 39% | +21% |
