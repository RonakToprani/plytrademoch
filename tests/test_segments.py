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
])
def test_segment_of(slug, expected):
    assert segment_of(slug) == expected


def test_props_win_over_winner_prefix():
    """A game slug with a structured suffix is a prop, not a winner market —
    order matters in _SEGMENTS and this is the ordering that matters most."""
    assert segment_of("nba-lal-bos-2026-08-02-spread") == "game-prop"
    assert segment_of("mlb-nym-cle-2026-08-05-total-8pt5") == "game-prop"
