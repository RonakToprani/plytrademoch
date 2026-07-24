"""
tests/test_edge.py — Edge-scoring math for the backtest harness.

Uses a fake feed (no network) so the P&L / ROI arithmetic and the cost model
are pinned down deterministically. Resolution is by winning *token id* — an
entry wins iff the whale's traded asset equals the token that settled to $1.
"""

from __future__ import annotations

from backtest.datafeed import Resolution, Trade
from backtest.edge import Entry, build_entries, score


class _FakeFeed:
    """Stand-in for DataFeed: returns canned resolutions by condition_id."""

    def __init__(self, winners: dict[str, str | None]) -> None:
        self._winners = winners

    def get_resolution(self, condition_id: str) -> Resolution | None:
        if condition_id not in self._winners:
            return None
        win = self._winners[condition_id]
        return Resolution(
            condition_id=condition_id,
            closed=win is not None,
            winning_token_id=win,
            end_date=None,
            fetched_at=0,
        )


def _entry(cond: str, asset: str, price: float, usd: float = 100.0) -> Entry:
    return Entry(ts=0, condition_id=cond, asset=asset, outcome_index=0,
                 price=price, usdc_size=usd, slug=cond)


def test_winner_roi_is_correct_with_zero_slippage():
    # Bought the winning token at 0.50 → $1 payout → +100% ROI.
    feed = _FakeFeed({"m": "WIN"})
    res = score([_entry("m", "WIN", 0.50)], feed, slippage=0.0, bootstrap_iters=100)
    assert res.n_entries == 1
    assert res.n_wins == 1
    assert abs(res.mean_roi - 1.0) < 1e-9


def test_loser_roi_is_minus_one():
    feed = _FakeFeed({"m": "WIN"})          # we bought "LOSE" → lost
    res = score([_entry("m", "LOSE", 0.50)], feed, slippage=0.0, bootstrap_iters=100)
    assert res.n_wins == 0
    assert abs(res.mean_roi + 1.0) < 1e-9


def test_slippage_erodes_edge():
    # Two bets at 0.50: one winner, one loser.
    feed = _FakeFeed({"w": "A", "l": "A"})
    entries = [_entry("w", "A", 0.50), _entry("l", "B", 0.50)]
    no_slip = score(entries, feed, slippage=0.0, bootstrap_iters=100)
    with_slip = score(entries, feed, slippage=0.03, bootstrap_iters=100)
    assert with_slip.mean_roi < no_slip.mean_roi


def test_unresolved_and_out_of_band_are_skipped():
    feed = _FakeFeed({"open": None, "resolved": "A"})
    entries = [
        _entry("open", "A", 0.50),        # unresolved → skip
        _entry("resolved", "A", 0.99),    # out of price band → skip
        _entry("resolved", "A", 0.40),    # counted (winner)
    ]
    res = score(entries, feed, min_price=0.08, max_price=0.92, bootstrap_iters=100)
    assert res.n_entries == 1
    assert res.n_resolved == 1


def test_build_entries_keeps_only_buys():
    trades = [
        Trade("w", 1, "m", "assetA", 0, "BUY", 0.5, 10, 100, "s", "t"),
        Trade("w", 2, "m", "assetA", 0, "SELL", 0.6, 10, 100, "s", "t"),
    ]
    entries = build_entries(trades)
    assert len(entries) == 1
    assert entries[0].asset == "assetA"
