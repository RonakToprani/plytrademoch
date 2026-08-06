"""
tests/test_live_sizing.py — the underdog scanner's calibration + sizing.

Guards the property the old flat-win-rate sizing got backwards: stake must track
where the measured edge actually is (peaks around 0.20-0.24), not fall away as
price rises and cut out entirely above 0.245.
"""

from __future__ import annotations

from backtest.live import (
    _NO_EDGE_SEGMENTS,
    _kelly_fraction,
    calibrated_win_rate,
    scan,
)


class FakeFeed:
    def __init__(self, markets):
        self._markets = markets

    def fetch_open_markets(self, min_volume=0.0):
        return [m for m in self._markets if m["volume"] >= min_volume]


def _market(slug, price, *, hours=48.0, volume=100_000.0, event=None):
    from datetime import datetime, timedelta, timezone
    end = datetime.now(timezone.utc) + timedelta(hours=hours)
    return {
        "condition_id": f"c-{slug}", "slug": slug, "question": slug,
        "tokens": [f"{slug}-t0", f"{slug}-t1"], "prices": [price, round(1 - price, 4)],
        "outcomes": ["Yes", "No"], "end_date": end.isoformat(),
        "volume": volume, "event": event or f"ev:{slug}",
    }


# --- calibration curve ----------------------------------------------------

def test_win_rate_rises_with_price_and_beats_it():
    """Every in-band price must imply a win rate above the price — that gap IS
    the edge. A flat constant cannot satisfy this across the whole band."""
    prev = 0.0
    for p in (0.15, 0.18, 0.21, 0.24, 0.27, 0.30, 0.33):
        q = calibrated_win_rate(p)
        assert q > p, f"no edge implied at {p}"
        assert q > prev, "win rate must be monotone in price"
        prev = q


def test_kelly_peaks_in_the_measured_sweet_spot_not_at_the_floor():
    f = {p: _kelly_fraction(p, calibrated_win_rate(p))
         for p in (0.15, 0.18, 0.21, 0.24, 0.27, 0.30, 0.33)}
    assert all(v > 0 for v in f.values()), "whole band must be tradeable"
    # the old bug: biggest stake at the floor, negative (skipped) above 0.245
    assert f[0.15] < f[0.21], "must not stake most at the weakest-edge price"
    assert max(f, key=f.get) in (0.21, 0.24), f"peak in the wrong place: {f}"
    # and the top of the band is emphatically still tradeable
    assert f[0.33] > f[0.15]


def test_old_flat_win_rate_would_have_refused_the_top_of_the_band():
    """Documents the defect this replaced, so it cannot quietly come back."""
    assert _kelly_fraction(0.25, 0.245) < 0
    assert _kelly_fraction(0.25, calibrated_win_rate(0.25)) > 0


# --- scan filtering -------------------------------------------------------

def test_scan_drops_no_edge_segments():
    # 2026-08-05 recalibration: game-WINNER markets (sportsbook-anchored, no edge
    # at realistic spread) are out; game PROPS (draws/exact scores/totals), plain
    # "other" questions and geopolitics stay in.
    assert "mention-count" in _NO_EDGE_SEGMENTS
    assert "game-winner" in _NO_EDGE_SEGMENTS
    feed = FakeFeed([
        _market("will-elon-musk-post-280-299-tweets-in-august", 0.20),
        _market("nba-lal-bos-2026-08-02", 0.20),          # winner: dropped
        _market("atp-tien-monfils-2026-08-05", 0.20),     # winner: dropped
        _market("cs2-tl1-9ine-2026-08-04", 0.20),         # esports winner: dropped
        _market("epl-ars-ips-2026-12-27-draw", 0.20),     # prop: kept
        _market("fifwc-kor-civ-2026-06-25-exact-score-0-3", 0.20),  # prop: kept
        _market("will-russia-capture-kostyantynivka-by-august-31", 0.20),  # kept
    ])
    slugs = {o.slug for o in scan(feed, bankroll=1_000.0)}
    assert slugs == {"epl-ars-ips-2026-12-27-draw",
                     "fifwc-kor-civ-2026-06-25-exact-score-0-3",
                     "will-russia-capture-kostyantynivka-by-august-31"}


def test_scan_drops_season_futures():
    """sports-season futures are -54.5% [-87.7,-11.0] when they enter the window
    (the final week of "win the World Series" is exactly when they appear)."""
    assert "sports-season" in _NO_EDGE_SEGMENTS
    feed = FakeFeed([
        _market("will-the-yankees-win-the-2026-world-series", 0.20, hours=100.0),
    ])
    assert scan(feed, bankroll=1_000.0) == []


def test_geopolitics_gets_the_extended_window():
    """Geopolitics is the one segment still an EDGE at 240h at both slippages
    (+29.5% [+6.9,+55.3] at slip 0.03); everything else stays capped at 168h."""
    feed = FakeFeed([
        _market("russia-x-ukraine-ceasefire-by-september", 0.20, hours=230.0),
        _market("will-something-odd-happen-by-september", 0.20, hours=230.0),
    ])
    slugs = {o.slug for o in scan(feed, bankroll=1_000.0)}
    assert slugs == {"russia-x-ukraine-ceasefire-by-september"}


def test_scan_respects_band_and_window():
    feed = FakeFeed([
        _market("in-band", 0.20),
        _market("too-cheap", 0.13),
        _market("too-rich", 0.40),
        _market("too-soon", 0.20, hours=2.0),
        _market("too-far", 0.20, hours=500.0),
        _market("too-thin", 0.20, volume=1_000.0),
    ])
    assert {o.slug for o in scan(feed, bankroll=1_000.0)} == {"in-band"}


def test_scan_keeps_one_leg_per_event():
    feed = FakeFeed([
        _market("leg-a", 0.20, volume=50_000.0, event="ev:same"),
        _market("leg-b", 0.20, volume=90_000.0, event="ev:same"),
    ])
    opps = scan(feed, bankroll=1_000.0)
    assert len(opps) == 1 and opps[0].slug == "leg-b"  # keeps the more liquid leg


def test_scan_skips_rather_than_rounding_sub_minimum_stakes_up():
    """On a tiny bankroll Kelly asks for cents; the answer is no bet, not $1."""
    feed = FakeFeed([_market("in-band", 0.20)])
    assert scan(feed, bankroll=10.0, min_stake=1.0) == []
    assert len(scan(feed, bankroll=1_000.0, min_stake=1.0)) == 1
