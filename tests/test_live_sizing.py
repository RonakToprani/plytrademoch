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
    for p in (0.15, 0.18, 0.21, 0.24, 0.27, 0.30):
        q = calibrated_win_rate(p)
        assert q > p, f"no edge implied at {p}"
        assert q > prev, "win rate must be monotone in price"
        prev = q


def test_kelly_peaks_in_the_measured_sweet_spot_not_at_the_floor():
    f = {p: _kelly_fraction(p, calibrated_win_rate(p))
         for p in (0.15, 0.18, 0.21, 0.24, 0.27, 0.30)}
    assert all(v > 0 for v in f.values()), "whole band must be tradeable"
    # the old bug: biggest stake at the floor, negative (skipped) above 0.245
    assert f[0.15] < f[0.21], "must not stake most at the weakest-edge price"
    assert max(f, key=f.get) in (0.21, 0.24), f"peak in the wrong place: {f}"
    # and the top of the band is emphatically still tradeable
    assert f[0.30] > f[0.15]


def test_old_flat_win_rate_would_have_refused_the_top_of_the_band():
    """Documents the defect this replaced, so it cannot quietly come back."""
    assert _kelly_fraction(0.25, 0.245) < 0
    assert _kelly_fraction(0.25, calibrated_win_rate(0.25)) > 0


# --- scan filtering -------------------------------------------------------

def test_scan_drops_no_edge_segments():
    assert "mention-count" in _NO_EDGE_SEGMENTS
    feed = FakeFeed([
        _market("will-elon-musk-post-280-299-tweets-in-august", 0.20),
        _market("nba-lal-bos-2026-08-02", 0.20),
    ])
    slugs = {o.slug for o in scan(feed, bankroll=1_000.0)}
    assert slugs == {"nba-lal-bos-2026-08-02"}


def test_scan_respects_band_and_window():
    feed = FakeFeed([
        _market("in-band", 0.20),
        _market("too-cheap", 0.13),
        _market("too-rich", 0.35),
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
