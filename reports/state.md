# Poly underdog paper state — 2026-08-06T19:59:08.361869+00:00

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
- open **8** ($103.85)  ·  settled **117** (19W / 98L)
- realized P&L **$-258.65**  ·  ROI **-22.2%** (backtest exp ~+19.8%)  ·  win **16%** (exp ~28.2%)
- last scan: 2026-08-06T19:47:38.076965+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| US announces end of Iranian blockade by August 7, 20 | Yes | 0.213 | $1.75 | 2026-08-07T23:59:07.628570+00:00 |
| Will Mike Lindell win the 2026 Minnesota Governor Re | No | 0.260 | $14.74 | 2026-08-11T00:00:05.318766+00:00 |
| Will Russell Fry be the new Republican nominee for S | Yes | 0.179 | $12.97 | 2026-08-11T00:00:06.077527+00:00 |
| Israel agrees to Board of Peace Gaza plan by August  | Yes | 0.264 | $14.79 | 2026-08-07T23:59:09.111374+00:00 |
| Will Francesca Hong win the 2026 Wisconsin Governor  | No | 0.178 | $11.40 | 2026-08-11T00:00:07.230552+00:00 |
| Will the next Google Gemini Pro model be released by | Yes | 0.256 | $14.90 | 2026-08-07T16:00:07.416769+00:00 |
| Dota 2: Ilbirs eSports vs Power Rangers (BO3) - EPL  | Ilbirs eSports | 0.270 | $14.83 | 2026-08-07T00:00:08.073620+00:00 |
| Will Ethereum reach $2,000 August 3-9? | Yes | 0.210 | $18.47 | 2026-08-10T04:00:07.800936+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
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
| National Bank Open: Ignacio Buse vs Cameron Norrie | LOST | -11.40 |
| T20 Lanka Premier League: Colombo Kaps vs Kandy Roya | LOST | -9.05 |
| Plovdiv 2: Petr Nesterov vs Sebastian Sorger | LOST | -9.05 |
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
| National Bank Open: Rebecca Sramkova vs Diana Shnaid | LOST | -14.92 |
| National Bank Open: Juncheng Shang vs Andrey Rublev | WON | +52.38 |
| Exact Score: CF Villarreal C 0 - 0 Levante UD? | LOST | -13.95 |
| Canadian Open: Pablo Carreno Busta vs Valentin Royer | LOST | -14.92 |
| National Bank Open: Jacob Fearnley vs Adrian Mannari | LOST | -14.95 |
| National Bank Open: Camila Osorio vs Ekaterina Alexa | LOST | -16.92 |
| The Hundred, Women: Sunrisers Leeds vs London Spirit | LOST | -14.92 |
| National Bank Open: Adam Walton vs Jenson Brooksby | LOST | -14.92 |
| Plovdiv 2: Hernan Casanova vs Yannick Alexandrescou | LOST | -13.15 |
| Grodzisk Mazowiecki: Alexander Donski vs Takuya Kuma | LOST | -12.53 |
| Warsaw: Linda Klimovicova vs Elizara Yaneva | WON | +91.93 |
| Hagen: Thiago Monteiro vs Tom Gentzsch | LOST | -9.05 |
| Warsaw: Marcelina Podlinska vs Vendula Valdmannova | LOST | -11.40 |
| Warsaw: Elsa Jacquemot vs Carol Young Suh Lee | LOST | -14.40 |
| Counter-Strike: Liquid vs 9INE (BO3) - Stake Pulse B | LOST | -14.40 |
| Dota 2: BetBoom Team vs OG (BO3) - 1win Essence Play | LOST | -14.40 |
| Bitcoin Up or Down on August 4? | LOST | -17.51 |
| National Bank Open: Xinyu Wang vs Daria Kasatkina | LOST | -17.39 |
| Canadian Open: Camilo Ugo Carabelli vs Cameron Norri | LOST | -17.35 |
| National Bank Open: Tatjana Maria vs Caty McNally | WON | +28.63 |
| St. Louis Cardinals vs. New York Yankees | WON | +44.19 |
| National Bank Open: Aleksandar Vukic vs Daniel Altma | WON | +75.17 |
| Los Angeles Dodgers vs. Chicago Cubs | LOST | -14.40 |
| Toronto Blue Jays vs. Houston Astros | LOST | -14.95 |

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
| 0.15–0.20 | 41 | 10% | -15% |
| 0.20–0.25 | 34 | 24% | -35% |
| 0.25–0.30 | 21 | 19% | -19% |
| 0.30–0.33 | 4 | 50% | +62% |
