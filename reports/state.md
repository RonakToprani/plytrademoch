# Poly underdog paper state — 2026-08-15T09:57:36.222752+00:00

**Strategy:** buy the underdog outcome token priced **0.15–0.33** on liquid
Polymarket markets resolving in **6–168h**; hold to resolution. Fractional-
Kelly sizing (against a price-calibrated win rate) on a $1,000 paper bankroll.
NEGATIVE SKEW (~28.2% win rate) — judge on realized ROI over dozens of settled
EVENTS, not bets and not the first few.

**Read `EXPECTATIONS.md` in this repo before grading these results.** It is the
source of truth for what 'working' looks like, recalibrated 2026-08-05 on
355,896 markets / 218,734 events. Key points a reviewer must not get wrong:

- Expect **~+19.8% ROI** (95% CI [+16.2%, +23.3%]) and a **~28.2% win rate**
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
- open **10** ($174.70)  ·  settled **144** (29W / 115L)
- realized P&L **$-53.17**  ·  ROI **-3.3%** (backtest exp ~+19.8%)  ·  win **20%** (exp ~28.2%)
- last scan: 2026-08-15T09:20:36.335780+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| Will Russell Fry be the new Republican nominee for S | Yes | 0.179 | $12.97 | 2026-08-11T00:00:06.077527+00:00 |
| US-Iran Hormuz Agreement by August 15? | Yes | 0.200 | $18.47 | 2026-08-15T23:59:07.291817+00:00 |
| Iran-Oman Hormuz Agreement by August 15? | No | 0.290 | $19.43 | 2026-08-15T23:59:07.952463+00:00 |
| Spread: St. Louis Cardinals (-1.5) | St. Louis Cardinals | 0.300 | $16.58 | 2026-08-17T17:40:07.602359+00:00 |
| US announces end of Iranian blockade by August 15, 2 | Yes | 0.170 | $14.59 | 2026-08-15T23:59:08.110477+00:00 |
| Will MrBeast's next video get between 80 and 90 mill | Yes | 0.232 | $19.88 | 2026-08-15T23:59:08.020816+00:00 |
| Will Bitcoin reach $66,000 August 10-16? | Yes | 0.190 | $17.20 | 2026-08-17T04:00:07.763667+00:00 |
| US-Iran 60 day negotiation period extended? | Yes | 0.250 | $19.43 | 2026-08-20T23:59:07.069534+00:00 |
| Will Australia win? | Yes | 0.330 | $15.89 | 2026-08-19T20:30:07.935672+00:00 |
| Bitcoin Up or Down on August 15? | Down | 0.250 | $20.26 | 2026-08-15T16:00:07.667875+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
| Bitcoin Up or Down on August 14? | LOST | -18.27 |
| Bitcoin Up or Down on August 13? | WON | +56.72 |
| ITF M25 Kursumlijska Banja 3 Men: George Lazarov vs  | LOST | -17.87 |
| Bitcoin Up or Down on August 12? | WON | +27.23 |
| Will Deportivo Toluca FC win on 2026-08-12? | LOST | -13.41 |
| Will FC Cincinnati win on 2026-08-11? | WON | +38.69 |
| Will the price of Bitcoin be above $64,000 on August | WON | +52.97 |
| Will Kai and Speed beat the Minecraft challenge by A | WON | +59.71 |
| Game Handicap: RED (-1.5) vs Leviatan Esports (+1.5) | WON | +32.26 |
| Bitcoin Up or Down on August 10? | LOST | -13.41 |
| Game Handicap: G2 (-1.5) vs Team Heretics (+1.5) | LOST | -16.68 |
| Will the next Google Gemini Pro model be released by | LOST | -12.23 |
| Bitcoin Up or Down on August 9? | WON | +73.09 |
| Will Independiente Santa Fe win on 2026-08-09? | LOST | -19.43 |
| Bitcoin Up or Down on August 8? | LOST | -13.41 |
| US announces end of Iranian blockade by August 9, 20 | LOST | -20.42 |
| Will Marcelo attend Cristiano Ronaldo's wedding? | LOST | -19.00 |
| Will the price of Bitcoin be above $64,000 on August | LOST | -17.22 |
| Bitcoin Up or Down on August 7? | WON | +35.23 |
| Will Bitcoin reach $66,000 August 3-9? | LOST | -19.00 |
| Will Ethereum reach $2,000 August 3-9? | LOST | -18.47 |
| Bitcoin Up or Down on August 6? | LOST | -19.43 |
| Athletics vs. Cincinnati Reds | LOST | -9.05 |
| Los Angeles Angels vs. Baltimore Orioles | LOST | -17.35 |
| Washington Nationals vs. Philadelphia Phillies | WON | +49.62 |
| Chicago White Sox vs. Boston Red Sox | LOST | -14.95 |
| Miami Marlins vs. Atlanta Braves | LOST | -14.92 |
| New York Mets vs. Cleveland Guardians | LOST | -13.15 |
| National Bank Open: Learner Tien vs Gael Monfils | LOST | -14.83 |
| National Bank Open: Alina Korneeva vs Emma Navarro | LOST | -14.90 |
| Tampa Bay Rays vs. Colorado Rockies | LOST | -14.83 |
| Los Angeles Dodgers vs. Chicago Cubs | LOST | -14.90 |
| Dota 2: Ilbirs eSports vs Power Rangers (BO3) - EPL  | LOST | -14.83 |
| National Bank Open: Ignacio Buse vs Cameron Norrie | LOST | -11.40 |
| T20 Lanka Premier League: Colombo Kaps vs Kandy Roya | LOST | -9.05 |
| Plovdiv 2: Petr Nesterov vs Sebastian Sorger | LOST | -9.05 |
| Will the next Google Gemini Pro model be released by | LOST | -14.90 |
| Warsaw: Weronika Falkowska vs Noma Noha Akugue | WON | +42.51 |
| The Hundred, Women: Trent Rockets vs Birmingham Phoe | LOST | -13.15 |
| Counter-Strike: Nuclear TigeRES vs CYBERSHOKE Prospe | LOST | -14.83 |
| Hagen: Maxim Mrva vs Guy Den Ouden | LOST | -17.02 |
| Grodzisk Mazowiecki: Amit Vales vs Daniil Glinka | LOST | -14.92 |
| Counter-Strike: Imperial vs ALKA (BO3) - BetBoom Sto | LOST | -14.04 |
| Warsaw: Katarzyna Kawa vs Justina Mikulskyte | WON | +34.77 |
| Warsaw: Carol Young Suh Lee vs Aliona Falei | WON | +42.53 |
| LoL: EDward Gaming vs Top Esports (BO3) - LPL Group  | LOST | -9.05 |
| LoL: JD Gaming vs LGD Gaming (BO3) - LPL Group Ascen | LOST | -14.74 |
| Will Francesca Hong win the 2026 Wisconsin Governor  | WON | +52.72 |
| Detroit Tigers vs. Seattle Mariners | LOST | -11.40 |
| San Diego Padres vs. Arizona Diamondbacks | LOST | -14.74 |
| Los Angeles Dodgers vs. Chicago Cubs | LOST | -9.05 |
| San Francisco Giants vs. Texas Rangers | LOST | -16.50 |
| St. Louis Cardinals vs. New York Yankees | LOST | -17.51 |
| National Bank Open: Anna Kalinskaya vs McCartney Kes | LOST | -16.54 |
| New York Mets vs. Cleveland Guardians | LOST | -14.92 |
| Los Angeles Angels vs. Baltimore Orioles | LOST | -14.95 |
| Washington Nationals vs. Philadelphia Phillies | LOST | -15.86 |
| National Bank Open: Kamilla Rakhimova vs Katerina Si | WON | +28.66 |
| Canadian Open: Lorenzo Sonego vs Tallon Griekspoor | LOST | -14.14 |
| Canadian Open: Giovanni Mpetshi Perricard vs Botic v | LOST | -14.92 |

## Edge by price band (out-of-sample, cached universe, 48h horizon)
| band | n | win% | mean px | buy ROI |
|---|---|---|---|---|
| 0.02–0.10 | 9946 | 7% | 0.051 | +11% |
| 0.12–0.15 | 2038 | 16% | 0.133 | +10% |
| 0.15–0.20 | 3399 | 23% | 0.173 | +25% |
| 0.15–0.25 | 7088 | 26% | 0.199 | +23% |
| 0.15–0.30 | 11221 | 28% | 0.226 | +20% |
| 0.15–0.33 | 13238 | 29% | 0.240 | +19% |
| 0.20–0.33 | 9839 | 32% | 0.263 | +16% |
| 0.30–0.33 | 2017 | 36% | 0.313 | +11% |
| 0.33–0.36 | 1915 | 37% | 0.343 | +4% |
| 0.36–0.40 | 2726 | 38% | 0.378 | -1% |
| 0.80–0.90 | 6885 | 80% | 0.849 | -7% |
| 0.90–0.98 | 10105 | 93% | 0.947 | -3% |

## Paper results by entry price
| bucket | n | win% | ROI |
|---|---|---|---|
| <0.15 | 17 | 6% | -54% |
| 0.15–0.20 | 45 | 13% | +8% |
| 0.20–0.25 | 38 | 24% | -22% |
| 0.25–0.30 | 33 | 21% | -12% |
| 0.30–0.33 | 11 | 55% | +81% |
