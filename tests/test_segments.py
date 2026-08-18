"""
tests/test_segments.py — the slug classifier that gates live flow.

The 2026-08-05 recalibration hangs on one distinction: game-WINNER markets
(sportsbook-anchored, no edge net of spread) vs game PROPS (draws, exact
scores, totals — where the favorite-longshot bias survives). If the classifier
drifts, the scanner starts buying efficient flow again, so pin it down.
"""

from __future__ import annotations

import pytest

from backtest.bigtest import segment_of


@pytest.mark.parametrize("slug,expected", [
    # winners — every sport the old classifier missed included
    ("mlb-nym-cle-2026-08-05", "game-winner"),
    ("nba-lal-bos-2026-08-02", "game-winner"),
    ("atp-tien-monfils-2026-08-05", "game-winner"),
    ("wta-korneev-navarro-2026-08-04", "game-winner"),
    ("cs2-tl1-9ine-2026-08-04", "game-winner"),
    ("lol-lng-esports-vs-invictus-gaming", "game-winner"),
    ("dota2-bb4-og-2026-08-04", "game-winner"),
    ("crichundredw-sun-lon-2026-08-04", "game-winner"),
    ("t20lpl-col-kan-2026-08-05", "game-winner"),
    ("ufc-fight-night-daniel-rodriguez-vs-uros-medic", "game-winner"),
    ("epl-bur-ars-2025-11-01-bur", "game-winner"),
    ("mls-mia-nas-2025-10-24-mia", "game-winner"),
    # props — structured markets stay tradeable
    ("epl-ars-ips-2024-12-27-draw", "game-prop"),
    ("mls-dal-rsl-2026-05-09-draw", "game-prop"),
    ("fifwc-kor-civ-2026-06-25-exact-score-0-3", "game-prop"),
    ("epl-bri-cry-2026-02-08-total-2pt5", "game-prop"),
    ("epl-mun-not-2026-05-17-total-1pt5", "game-prop"),
    # the rest of the taxonomy still routes as before
    ("will-elon-musk-post-280-299-tweets-in-august", "mention-count"),
    ("fed-decision-in-september", "fed-macro"),
    ("will-bitcoin-reach-66000-july-27-august-2", "crypto-price"),
    ("israel-x-iran-ceasefire-continues-through-august-2", "geopolitics"),
    ("will-shri-thanedar-be-the-democratic-nominee-for-mi-13", "election"),
    ("will-moonshot-have-the-best-chinese-ai-model", "other"),

    # --- 2026-08-17 leak audit: all of these used to classify as `other`, i.e.
    # they were BUYABLE despite belonging to excluded segments. ---
    # Match-shaped slugs from leagues absent from the prefix whitelist. Measured
    # +12.3% [+5.7,+19.1] @slip 0.01 but n.s. at 0.03 — the game-winner signature.
    ("cbb-uconn-mich-2026-04-06", "game-winner"),
    ("cfb-mia-ind-2026-01-19", "game-winner"),
    ("sea-tor-juv-2026-05-24-juv", "game-winner"),
    ("bun-pad-wol-2026-05-25-wol", "game-winner"),
    ("fl1-nic-se-2026-05-29-se", "game-winner"),
    ("crint-afg-lka-2026-03-13", "game-winner"),
    ("itf-lene-curmi-2026-07-31", "game-winner"),
    ("bkcba-sha3-zhe-2026-06-05", "game-winner"),
    # Season/tournament futures beyond the four US majors.
    ("will-kimi-antonelli-be-the-2026-f1-drivers-champion", "sports-season"),
    ("will-t1-win-the-lck-2026-season-playoffs", "sports-season"),
    ("will-team-falcons-win-the-cs2-ewc-2026", "sports-season"),
    ("will-the-utah-jazz-win-the-nba-western-conference-finals", "sports-season"),
    ("will-zac-mcgraw-win-2026-mls-defender-of-the-year", "sports-season"),
    ("will-khamzat-chimaev-be-the-ufc-middleweight-champion-on-december-31-2026",
     "sports-season"),
    # Races that never say "election" — seven live midterm markets were buyable.
    ("will-the-democrats-win-the-maine-senate-race-in-2026", "election"),
    ("will-the-republicans-win-the-michigan-governor-race-in-2026", "election"),
    ("will-afd-win-an-absolute-majority-of-seats-in-sachsen-anhalt", "election"),
    ("will-another-party-win-the-most-seats", "election"),
    # Central-bank rate decisions the `^fed-` prefix missed.
    ("will-the-upper-bound-of-the-target-federal-funds-rate-be-4pt0-at-the-end-of-2026",
     "fed-macro"),
    ("will-the-bank-of-japan-announce-a-25-bps-increase-at-the-september-2026-meeting",
     "fed-macro"),
    ("will-the-ecb-announce-no-change-at-the-july-2026-meeting", "fed-macro"),
    # ...but NOT central-bank personnel: no futures curve anchors these, so they
    # stay in the tradeable bucket. An earlier draft matched bare "powell" and
    # swallowed an unrelated UK cabinet market.
    ("jerome-powell-out-from-fed-board-by-december-31", "other"),
    ("will-lucy-powell-be-the-next-culture-secretary-of-the-uk-in-2026", "other"),
])
def test_segment_of(slug, expected):
    assert segment_of(slug) == expected


def test_match_shape_does_not_eat_dated_non_sports_markets():
    """The shape rule is `league-team-team-YYYY-MM-DD`. Ordinary dated questions
    have prose between the words and must stay tradeable."""
    assert segment_of("us-announces-end-of-iranian-blockade-by-august-7-2026") != "game-winner"
    assert segment_of("will-openai-ipo-by-december-31-2026") == "other"
    assert segment_of("nothing-ever-happens-2026") == "other"


def test_props_still_win_over_the_match_shape():
    """game-prop is tested before game-winner, so a prop suffix on a match-shaped
    slug keeps it tradeable — this is the ordering the shape rule could break."""
    assert segment_of("mls-dal-rsl-2026-05-09-draw") == "game-prop"
    assert segment_of("fifwc-kor-civ-2026-06-25-exact-score-0-3") == "game-prop"
    assert segment_of("bun-pad-wol-2026-05-25-total-2pt5") == "game-prop"


def test_props_win_over_winner_prefix():
    """A game slug with a structured suffix is a prop, not a winner market —
    order matters in _SEGMENTS and this is the ordering that matters most."""
    assert segment_of("nba-lal-bos-2026-08-02-spread") == "game-prop"
    assert segment_of("mlb-nym-cle-2026-08-05-total-8pt5") == "game-prop"
