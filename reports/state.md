# Poly underdog paper state — 2026-10-02T22:58:08.836297+00:00

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
- open **12** ($190.88)  ·  settled **348** (80W / 268L)
- realized P&L **$-91.82**  ·  ROI **-1.8%** (backtest exp ~+20.3%)  ·  win **23%** (exp ~29.6%)
- last scan: 2026-10-02T22:23:22.887480+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| Will Elif Eralp be the next Governing Mayor of Berli | No | 0.304 | $16.52 | 2026-09-20T23:59:07.655567+00:00 |
| 0 ships transit Hormuz on any date by September 30? | Yes | 0.248 | $18.47 | 2026-10-01T03:59:08.177054+00:00 |
| Will Trump meet with Javier Milei in September 2026? | No | 0.180 | $14.53 | 2026-10-01T03:59:08.157770+00:00 |
| Will Russia target Kyiv on October 4, 2026? | No | 0.228 | $20.42 | 2026-10-05T03:59:08.076246+00:00 |
| Will MrBeast Gaming's next video get between 30 and  | No | 0.191 | $15.88 | 2026-10-03T23:59:07.235740+00:00 |
| Will Bitcoin reach $90,000 September 28-October 4? | Yes | 0.180 | $16.47 | 2026-10-05T04:00:07.566966+00:00 |
| Flávio Bolsonaro participates in debate before first | Yes | 0.285 | $12.88 | 2026-10-04T02:59:07.476162+00:00 |
| Will the price of Bitcoin be above $84,000 on Octobe | No | 0.178 | $19.43 | 2026-10-03T16:00:07.801105+00:00 |
| Will Ethereum dip to $2,600 September 28-October 4? | Yes | 0.245 | $16.44 | 2026-10-05T04:00:08.350905+00:00 |
| Spread: Burkina Faso (-5.5) | Burkina Faso | 0.298 | $11.84 | 2026-10-03T20:00:08.272477+00:00 |
| Will Argentina vs. Burkina Faso end in a draw? | Yes | 0.170 | $14.59 | 2026-10-03T20:00:07.967662+00:00 |
| Map Handicap: GLS (-1.5) vs Grêmio Esports (+1.5) | Grêmio Esports | 0.330 | $13.41 | 2026-10-03T04:00:08.006024+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
| Will the price of Ethereum be above $2,800 on Octobe | LOST | -18.33 |
| Bitcoin Up or Down on October 2? | LOST | -18.61 |
| Will the price of Bitcoin be above $82,000 on Octobe | LOST | -16.53 |
| Bitcoin Up or Down on October 1? | WON | +74.74 |
| Map Handicap: FaZe (-1.5) vs Nemiga (+1.5) | LOST | -16.47 |
| Will Wales vs. Norway end in a draw? | LOST | -18.47 |
| Spread: Browns (-3.5) | LOST | -16.58 |
| Will Bitcoin reach $86,000 September 28-October 4? | LOST | -16.53 |
| Will there be no next Google Gemini Pro model releas | LOST | -12.88 |
| Will the next Google Gemini Pro model be released by | LOST | -12.36 |
| Chicago White Sox vs. Houston Astros: O/U 8.5 | LOST | -10.93 |
| Gemini 4.0 released by September 30, 2026? | LOST | -12.88 |
| Philadelphia Phillies vs. Atlanta Braves: O/U 6.5 | WON | +51.66 |
| Iran charges Hormuz fees by September 30? | LOST | -12.10 |
| Next US-Iran senior diplomatic meeting by September  | LOST | -17.22 |
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
| Will Russia enter Mykolaivka by September 30, 2026? | WON | +37.35 |
| Map Handicap: paiN (-1.5) vs Galorys (+1.5) | WON | +44.28 |
| Will George Russell win the 2026 F1 Azerbaijan Grand | LOST | -20.42 |
| Will England vs. Spain end in a draw? | LOST | -17.22 |
| Will the price of Bitcoin be above $84,000 on Septem | LOST | -21.08 |
| Bitcoin Up or Down on September 26? | LOST | -16.47 |
| Spread: Steelers (-3.5) | LOST | -17.22 |
| Spread: Colts (-3.5) | LOST | -13.41 |
| Spread: Broncos (-3.5) | WON | +33.77 |
| Spread: Cowboys (-3.5) | LOST | -18.61 |
| Will Xiaomi have the best Chinese AI model at the en | LOST | -19.98 |
| Will MrBeast's next video get between 70 and 80 mill | LOST | -16.63 |
| US-Iran Hormuz Agreement by September 30? | LOST | -13.94 |
| Will Russia capture all of Chasiv Yar by September 3 | LOST | -15.88 |
| Map Handicap: KC (-1.5) vs XLG Gaming (+1.5) | LOST | -17.57 |
| Bitcoin Up or Down on September 25? | WON | +34.87 |
| Saudi Oil Pipeline (East-West) restarts by September | LOST | -13.41 |
| Will XRP reach $1.80 in September? | LOST | -12.36 |
| Russia-Ukraine peace talks by September 30, 2026? | LOST | -19.24 |
| Will the price of Bitcoin be above $82,000 on Septem | LOST | -19.51 |
| Bitcoin Up or Down on September 24? | WON | +65.05 |
| Will the price of Bitcoin be above $84,000 on Septem | WON | +63.63 |
| CNN, Politico, or MS NOW unbanned from White House b | LOST | -12.23 |
| Will Solana reach $130 in September? | LOST | -10.93 |
| Will Russia and Ukraine hold any diplomatic meeting  | LOST | -17.87 |
| Trump renames AI by September 30? | WON | +48.45 |
| Will Ethereum reach $2,900 in September? | LOST | -18.95 |
| Will Bitcoin reach $90,000 in September? | LOST | -12.62 |
| Will Anthropic have the best Code Arena | WebDev AI  | LOST | -15.88 |
| Will Bitcoin reach $88,000 September 21-27? | WON | +28.50 |
| Will the next Claude Opus model be released on Septe | LOST | -19.93 |
| US announces end of Iranian blockade by September 30 | LOST | -14.59 |
| Will the price of Bitcoin be above $86,000 on Septem | WON | +71.84 |

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
| 0.15–0.20 | 90 | 12% | -22% |
| 0.20–0.25 | 85 | 29% | +30% |
| 0.25–0.30 | 89 | 22% | -15% |
| 0.30–0.33 | 67 | 34% | +4% |
