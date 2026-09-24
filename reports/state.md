# Poly underdog paper state — 2026-09-24T05:46:38.532600+00:00

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
- open **11** ($169.87)  ·  settled **289** (68W / 221L)
- realized P&L **$74.42**  ·  ROI **+1.8%** (backtest exp ~+20.3%)  ·  win **24%** (exp ~29.6%)
- last scan: 2026-09-24T05:12:46.345200+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| US x Iran ceasefire continues through September 25? | No | 0.169 | $18.95 | 2026-09-25T23:59:07.243161+00:00 |
| Will Elif Eralp be the next Governing Mayor of Berli | No | 0.304 | $16.52 | 2026-09-20T23:59:07.655567+00:00 |
| US announces end of Iranian blockade by September 30 | Yes | 0.160 | $14.59 | 2026-10-01T03:59:07.348144+00:00 |
| Will Bitcoin reach $88,000 September 21-27? | No | 0.320 | $13.41 | 2026-09-28T04:00:08.387678+00:00 |
| Will Anthropic have the best Code Arena | WebDev AI  | No | 0.200 | $15.88 | 2026-09-30T16:00:07.723560+00:00 |
| Will Bitcoin reach $90,000 in September? | Yes | 0.156 | $12.62 | 2026-10-01T04:00:07.584059+00:00 |
| Will Ethereum reach $2,900 in September? | Yes | 0.210 | $18.95 | 2026-10-01T04:00:08.368131+00:00 |
| Trump renames AI by September 30? | Yes | 0.270 | $17.92 | 2026-10-01T03:59:09.095486+00:00 |
| Will Russia and Ukraine hold any diplomatic meeting  | Yes | 0.208 | $17.87 | 2026-10-01T03:59:19.832229+00:00 |
| Will Solana reach $130 in September? | Yes | 0.188 | $10.93 | 2026-10-01T04:00:20.511319+00:00 |
| CNN, Politico, or MS NOW unbanned from White House b | No | 0.167 | $12.23 | 2026-10-01T03:59:31.343370+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
| Will the next Claude Opus model be released on Septe | LOST | -19.93 |
| Will the price of Bitcoin be above $86,000 on Septem | WON | +71.84 |
| Will the price of Bitcoin be above $82,000 on Septem | WON | +40.57 |
| Will the price of Bitcoin be above $80,000 on Septem | LOST | -20.18 |
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
| US announces end of Iranian blockade by September 21 | LOST | -10.93 |
| Game Spread: Shelton (-4.5) vs Tiafoe (+4.5) | LOST | -16.63 |
| Iran-Oman Hormuz Agreement by September 14? | LOST | -21.08 |
| Game Spread: Zverev (-5.5) vs Khachanov (+5.5) | WON | +43.95 |
| Will the price of Bitcoin be above $78,000 on Septem | LOST | -15.89 |
| Will the Fed decide differently in the next three de | LOST | -20.42 |
| S&P 500 (SPX) Up or Down on September 11? | LOST | -16.68 |
| Will Bitcoin dip to $74,000 September 7-13? | LOST | -20.42 |
| Will the price of Bitcoin be above $76,000 on Septem | LOST | -18.56 |
| US x Iran Effective Ceasefire by September 11? | LOST | -13.41 |
| Bitcoin Up or Down on September 10? | LOST | -16.68 |
| Map Handicap: AST (-1.5) vs 5star (+1.5) | WON | +46.08 |
| Will Russia and Ukraine hold any diplomatic meeting  | LOST | -10.93 |
| Map Handicap: TYLOO (-1.5) vs Alliance (+1.5) | LOST | -16.68 |
| Israel x Lebanon diplomatic meeting by September 15, | WON | +56.86 |
| Will the price of Bitcoin be above $80,000 on Septem | LOST | -17.92 |
| Map Handicap: 9z (-1.5) vs MIBR (+1.5) | LOST | -16.47 |
| Map Handicap: G2.A (-1.5) vs Azuolas (+1.5) | LOST | -21.08 |
| Will the price of Bitcoin be above $78,000 on Septem | LOST | -14.59 |
| Map Handicap: MGLZ (-1.5) vs MIBR (+1.5) | LOST | -17.92 |
| Map Handicap: 9z (-1.5) vs 5star (+1.5) | LOST | -18.61 |
| Bitcoin Up or Down on September 7? | LOST | -18.27 |
| Will the price of Bitcoin be above $80,000 on Septem | LOST | -18.47 |
| Will the Bank of Russia make no change to the key ra | LOST | -16.41 |
| Will AfD win between 42% and 45% of all valid second | LOST | -21.08 |
| Will Kimi Antonelli win the 2026 F1 Italian Grand Pr | LOST | -16.47 |
| Israel military action against Lebanon on September  | LOST | -18.95 |
| Will the price of Bitcoin be above $80,000 on Septem | LOST | -15.89 |
| Bitcoin Up or Down on September 5? | LOST | -13.41 |
| Will the price of Bitcoin be above $80,000 on Septem | LOST | -20.26 |
| Map Handicap: FAL (-1.5) vs G2 (+1.5) | WON | +33.77 |
| Will OpenAI’s Astra model be released by September 4 | WON | +69.83 |
| Will the price of Bitcoin be above $80,000 on Septem | LOST | -17.92 |

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
| 0.15–0.20 | 73 | 15% | +2% |
| 0.20–0.25 | 74 | 28% | +22% |
| 0.25–0.30 | 69 | 23% | -12% |
| 0.30–0.33 | 56 | 34% | +2% |
