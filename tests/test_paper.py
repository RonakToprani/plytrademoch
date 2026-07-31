"""
tests/test_paper.py — PaperStore persistence logic (record/dedup/settle/stats).
Pure, no network — uses a temp DB.
"""

from __future__ import annotations

from datetime import datetime, timezone

from paper.store import Bet, PaperStore


def _bet(cond: str, token: str, price: float = 0.15, stake: float = 5.0) -> Bet:
    return Bet(
        id=None, condition_id=cond, token_id=token, slug=cond, question="Q?",
        outcome="Yes", entry_price=price, stake_usd=stake,
        shares=round(stake / price, 4), opened_at=datetime.now(timezone.utc).isoformat(),
        resolves_at=None,
    )


def _store(tmp_path):
    return PaperStore(str(tmp_path / "paper_test.db"))


def test_record_and_dedup_open_per_market(tmp_path):
    s = _store(tmp_path)
    assert s.record_bet(_bet("c1", "tokA")) is not None
    # second OPEN bet on the same market is rejected by the partial unique index
    assert s.record_bet(_bet("c1", "tokA")) is None
    assert len(s.open_bets()) == 1
    assert s.has_open("c1") is True
    assert s.has_open("c2") is False


def test_settle_won_pnl_and_stats(tmp_path):
    s = _store(tmp_path)
    bid = s.record_bet(_bet("c1", "tokA", price=0.10, stake=5.0))  # 50 shares
    # won → payout = 50*$1 = $50, pnl = 50 - 5 = 45
    s.settle_bet(bid, "WON", 1.0, 45.0)
    st = s.stats()
    assert st["settled"] == 1 and st["won"] == 1
    assert st["win_rate"] == 1.0
    assert st["realized_pnl"] == 45.0
    assert st["open"] == 0
    # can re-open the same market once the prior bet is settled
    assert s.record_bet(_bet("c1", "tokA")) is not None


def test_settle_lost_and_mixed_winrate(tmp_path):
    s = _store(tmp_path)
    a = s.record_bet(_bet("c1", "tokA"))
    b = s.record_bet(_bet("c2", "tokB"))
    s.settle_bet(a, "WON", 1.0, 28.0)
    s.settle_bet(b, "LOST", 0.0, -5.0)
    st = s.stats()
    assert st["won"] == 1 and st["lost"] == 1
    assert abs(st["win_rate"] - 0.5) < 1e-9
    assert st["realized_pnl"] == 23.0


def _ev_bet(cond: str, event: str, resolves: str | None = None, stake: float = 5.0) -> Bet:
    b = _bet(cond, "tok" + cond, stake=stake)
    b.event = event
    b.resolves_at = resolves
    return b


def test_has_open_event_blocks_correlated_legs(tmp_path):
    """
    The scanner dedupes events only inside one scan, so the store is what stops a
    later cycle adding a second leg of an event we already hold — the bug that let
    the book accumulate 6 Elon tweet-count buckets and 8 Iran legs.
    """
    s = _store(tmp_path)
    assert s.record_bet(_ev_bet("c1", "neg:elon-tweets")) is not None
    # different market (passes the condition_id index) but the SAME event
    assert s.has_open_event("neg:elon-tweets") is True
    # an unrelated event is still allowed
    assert s.has_open_event("ev:fed-july") is False


def test_has_open_event_ignores_empty_and_clears_on_settle(tmp_path):
    s = _store(tmp_path)
    # bets predating the event column must not all collide on ""
    assert s.has_open_event("") is False
    bid = s.record_bet(_ev_bet("c1", "ev:iran"))
    assert s.has_open_event("ev:iran") is True
    s.settle_bet(bid, "LOST", 0.0, -5.0)
    # once settled the event is tradeable again
    assert s.has_open_event("ev:iran") is False


def test_open_stake_on_resolve_date(tmp_path):
    s = _store(tmp_path)
    s.record_bet(_ev_bet("c1", "ev:a", resolves="2026-07-31T23:59:00+00:00", stake=6.0))
    s.record_bet(_ev_bet("c2", "ev:b", resolves="2026-07-31T04:00:00+00:00", stake=4.0))
    s.record_bet(_ev_bet("c3", "ev:c", resolves="2026-08-02T04:00:00+00:00", stake=9.0))
    assert s.open_stake_on("2026-07-31") == 10.0
    assert s.open_stake_on("2026-08-02") == 9.0
    assert s.open_stake_on("2026-09-01") == 0.0
