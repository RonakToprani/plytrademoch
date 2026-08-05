# Poly underdog paper state — 2026-08-05T16:16:44.080307+00:00

**Strategy:** buy the underdog outcome token priced **0.15–0.30** on liquid
Polymarket markets resolving in **6–168h**; hold to resolution. Fractional-
Kelly sizing (against a price-calibrated win rate) on a $1,000 paper bankroll.
NEGATIVE SKEW (~27.4% win rate) — judge on realized ROI over dozens of settled
EVENTS, not bets and not the first few.

**Read `EXPECTATIONS.md` in this repo before grading these results.** It is the
source of truth for what 'working' looks like, recalibrated 2026-08-03 on
355,896 markets / 218,734 events. Key points a reviewer must not get wrong:

- Expect **~+15.7% ROI** (95% CI [+12.5%, +18.9%]) and a **~27.4% win rate**.
  The older '+50–70% ROI / ~27% win' figures came from n=126 and are RETIRED —
  grading against them marks an on-spec strategy as underperforming.
- **Count settled EVENTS, not bets.** Correlated legs are not independent
  observations: 38 early paper bets spanned only 13 events, and a -50% result
  that looked catastrophic was P=59.6% under a real edge. Bets now carry an
  `event` key and only one open bet per event is allowed.
- **Losing streaks are expected.** At ~27% win, 10 straight losses has
  probability ~4.3%. Distinguishing +16% from 0 needs ~100+ settled events;
  below ~30 the honest answer is 'not yet knowable'.
- **Results before 2026-08-03 are contaminated** and should not be read as a
  verdict on the strategy. Two defects, both now fixed: fills were allowed
  0.03 BELOW the band floor, into a slice measured at +2.3% (not significant),
  and those sub-floor bets account for essentially the entire realized loss
  (-$96 of -$101); and a 3-day resolution cache left resolved bets sitting
  open, so the book reported 0W/17L while 3 of those bets had already won.

## Book
- open **15** ($160.76)  ·  settled **95** (17W / 78L)
- realized P&L **$-106.59**  ·  ROI **-12.0%** (backtest exp ~+15.7%)  ·  win **18%** (exp ~27.4%)
- last scan: 2026-08-05T16:08:51.065308+00:00

## Open positions
| market | side | entry | stake | resolves |
|---|---|---|---|---|
| Israel x Iran ceasefire continues through August 2? | No | 0.110 | $7.08 | 2026-08-02T23:59:07.589500+00:00 |
| Will Donavan McKinney be the Democratic Nominee for  | No | 0.190 | $4.32 | 2026-08-04T00:00:07.524388+00:00 |
| Will Shri Thanedar be the Democratic Nominee for MI- | Yes | 0.190 | $3.91 | 2026-08-04T00:00:07.374051+00:00 |
| US announces end of Iranian blockade by August 7, 20 | Yes | 0.213 | $1.75 | 2026-08-07T23:59:07.628570+00:00 |
| Will Mike Lindell win the 2026 Minnesota Governor Re | No | 0.260 | $14.74 | 2026-08-11T00:00:05.318766+00:00 |
| Will Russell Fry be the new Republican nominee for S | Yes | 0.179 | $12.97 | 2026-08-11T00:00:06.077527+00:00 |
| Israel agrees to Board of Peace Gaza plan by August  | Yes | 0.264 | $14.79 | 2026-08-07T23:59:09.111374+00:00 |
| Will Francesca Hong win the 2026 Wisconsin Governor  | No | 0.178 | $11.40 | 2026-08-11T00:00:07.230552+00:00 |
| LoL: EDward Gaming vs Top Esports (BO3) - LPL Group  | EDward Gaming | 0.160 | $9.05 | 2026-08-05T17:00:07.532798+00:00 |
| Counter-Strike: Imperial vs ALKA (BO3) - BetBoom Sto | ALKA | 0.200 | $14.04 | 2026-08-06T02:00:07.834728+00:00 |
| Counter-Strike: Nuclear TigeRES vs CYBERSHOKE Prospe | CYBERSHOKE Prospects | 0.270 | $14.83 | 2026-08-05T20:00:07.915865+00:00 |
| The Hundred, Women: Trent Rockets vs Birmingham Phoe | Birmingham Phoenix | 0.173 | $13.15 | 2026-08-12T10:00:07.789896+00:00 |
| Warsaw: Weronika Falkowska vs Noma Noha Akugue | Weronika Falkowska | 0.258 | $14.78 | 2026-08-12T08:00:07.468757+00:00 |
| Will the next Google Gemini Pro model be released by | Yes | 0.256 | $14.90 | 2026-08-07T16:00:07.416769+00:00 |
| Plovdiv 2: Petr Nesterov vs Sebastian Sorger | Sebastian Sorger | 0.280 | $9.05 | 2026-08-12T13:30:08.160253+00:00 |

## Settled
| market | result | P&L |
|---|---|---|
| Hagen: Maxim Mrva vs Guy Den Ouden | LOST | -17.02 |
| Grodzisk Mazowiecki: Amit Vales vs Daniil Glinka | LOST | -14.92 |
| Warsaw: Katarzyna Kawa vs Justina Mikulskyte | WON | +34.77 |
| Warsaw: Carol Young Suh Lee vs Aliona Falei | WON | +42.53 |
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
| Tampa Bay Rays vs. Colorado Rockies | LOST | -14.83 |
| Canadian Open: Kamil Majchrzak vs Gael Monfils | WON | +46.62 |
| San Francisco Giants vs. Texas Rangers | LOST | -17.51 |
| Pittsburgh Pirates vs. Milwaukee Brewers | LOST | -16.92 |
| Washington Nationals vs. Philadelphia Phillies | WON | +52.60 |
| Will Elon Musk post <40 tweets from August 1 to Augu | WON | +7.11 |
| Will the price of Bitcoin be above $62,000 on August | LOST | -3.99 |
| Will Spider-Man: Brand New Day beat Avengers: Endgam | LOST | -3.59 |
| LoL: LNG Esports vs Invictus Gaming (BO3) - LPL Grou | LOST | -2.33 |
| LoL: KT Rolster vs Hanwha Life Esports (BO3) - LCK R | WON | +3.17 |
| Bitcoin Up or Down on August 2? | LOST | -2.55 |
| Counter-Strike: Spirit vs MOUZ (BO5) - BLAST Bounty  | WON | +5.07 |
| UFC Fight Night: Daniel Rodriguez vs. Uroš Medic (We | LOST | -1.00 |
| UFC Fight Night: Jan Blachowicz vs. Navajo Stirling  | LOST | -1.00 |
| UFC Fight Night: Oban Elliott vs. Michael Oliveira ( | LOST | -1.00 |
| Will Elon Musk post 280-299 tweets from July 28 to A | LOST | -2.91 |
| Will "Spider-Man: Brand New Day" score at least 90 o | LOST | -1.00 |
| UFC Fight Night: Marcin Tybura vs. Aleksandar Rakic  | LOST | -1.00 |
| Will "Spider-Man: Brand New Day" Opening Weekend Box | LOST | -3.91 |

## Edge by price band (out-of-sample, cached universe, 48h horizon)
| band | n | win% | mean px | buy ROI |
|---|---|---|---|---|
| 0.02–0.10 | 11567 | 7% | 0.051 | +6% |
| 0.12–0.15 | 2590 | 15% | 0.133 | +2% |
| 0.15–0.20 | 4488 | 22% | 0.173 | +19% |
| 0.15–0.25 | 9608 | 25% | 0.200 | +18% |
| 0.15–0.30 | 15407 | 27% | 0.228 | +16% |
| 0.20–0.30 | 10919 | 30% | 0.250 | +14% |
| 0.30–0.33 | 3226 | 35% | 0.313 | +8% |
| 0.33–0.36 | 3196 | 36% | 0.343 | +3% |
| 0.80–0.90 | 8895 | 81% | 0.848 | -6% |
| 0.90–0.98 | 11761 | 93% | 0.947 | -3% |

## Paper results by entry price
| bucket | n | win% | ROI |
|---|---|---|---|
| <0.15 | 16 | 6% | -51% |
| 0.15–0.20 | 32 | 12% | +18% |
| 0.20–0.25 | 29 | 28% | -18% |
| 0.25–0.30 | 18 | 22% | -18% |
