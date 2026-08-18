"""
tests/test_review.py — the band-change decision rule in the nightly review.

The review's job is to say when the live band should move. It got this wrong
twice: on 2026-08-07/08 it recommended extending the floor off a point estimate
whose CI was [-1.4, +20.6] (pure noise), and after the 08-17 classifier fixes it
printed "has no significant edge" next to a CI of [+2%, +25%] — a slice that
excludes zero. Both bugs are wording collapsing three distinct states into two,
so pin the three states.
"""

from __future__ import annotations

import paper.review as review


def _cell(roi, ci_lo, ci_hi, n=1000):
    return {"n": n, "events": n, "win_rate": 0.2, "mean_price": 0.13,
            "buy_roi": roi, "ci_lo": ci_lo, "ci_hi": ci_hi}


def test_ci_including_zero_is_not_significant(monkeypatch):
    monkeypatch.setattr(review, "_stress_roi", lambda *a, **k: None)
    clears, why = review._band_change_verdict(_cell(0.10, -0.014, 0.206), (0.12, 0.15))
    assert clears is False
    assert "no significant edge" in why


def test_significant_but_under_the_bar_is_not_called_insignificant(monkeypatch):
    """The 08-17 regression: CI [+1.4%, +25.7%] excludes zero, so calling it
    'no significant edge' contradicts the number printed beside it."""
    monkeypatch.setattr(review, "_stress_roi", lambda *a, **k: None)
    clears, why = review._band_change_verdict(_cell(0.133, 0.014, 0.257), (0.12, 0.15))
    assert clears is False
    assert "no significant edge" not in why
    assert "below the bar" in why


def test_clears_the_bar_but_dies_at_slip_003(monkeypatch):
    """0.12-0.15 on the cleaned universe: real at slip 0.01, gone at 0.03.
    The stress test is the decision rule, not the 0.01 point estimate."""
    monkeypatch.setattr(review, "_stress_roi",
                        lambda *a, **k: {"n": 1793, "buy_roi": -0.006,
                                         "ci_lo": -0.111, "ci_hi": 0.102})
    clears, why = review._band_change_verdict(_cell(0.18, 0.09, 0.27), (0.12, 0.15))
    assert clears is False
    assert "does NOT survive" in why


def test_clears_the_bar_and_survives_slip_003(monkeypatch):
    monkeypatch.setattr(review, "_stress_roi",
                        lambda *a, **k: {"n": 1793, "buy_roi": 0.09,
                                         "ci_lo": 0.04, "ci_hi": 0.14})
    clears, why = review._band_change_verdict(_cell(0.18, 0.09, 0.27), (0.12, 0.15))
    assert clears is True
    assert "survives slip 0.03" in why


def test_missing_stress_data_never_recommends_a_change(monkeypatch):
    """No deep universe (legacy cache path) must fail closed: a band change is
    the one recommendation that must never fire on absent evidence."""
    monkeypatch.setattr(review, "_stress_roi", lambda *a, **k: None)
    clears, _ = review._band_change_verdict(_cell(0.25, 0.15, 0.35), (0.33, 0.36))
    assert clears is False


def test_no_significance_estimate_fails_closed(monkeypatch):
    monkeypatch.setattr(review, "_stress_roi", lambda *a, **k: None)
    clears, why = review._band_change_verdict(_cell(0.40, None, None), (0.33, 0.36))
    assert clears is False
    assert "no significance estimate" in why
