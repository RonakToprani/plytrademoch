"""
paper/engine.py — one paper-trading cycle: settle, then scan & record.

A cycle is idempotent and safe to run on any schedule (launchd/cron):
  1. Settle every OPEN bet whose market has resolved (CLOB winner flag).
  2. Scan open markets for underdog opportunities (backtest.live), verify each
     against the live order book (backtest.depth), and record a paper bet at the
     real VWAP fill price — skipping markets we already hold and respecting the
     exposure cap.

Places no orders. All P&L is simulated at resolution ($1 win / $0 loss).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backtest.depth import analyze as analyze_depth
from backtest.live import scan as scan_live
from backtest.datafeed import DataFeed
from paper.notify import PaperNotifier
from paper.store import Bet, PaperStore
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CycleResult:
    opportunities: int
    opened: int
    settled: int
    stats: dict


class PaperTrader:
    def __init__(
        self,
        *,
        bankroll: float = 150.0,
        band_lo: float = 0.10,
        band_hi: float = 0.20,
        min_hours: float = 24.0,
        max_hours: float = 96.0,   # 1-4 day holds: edge is as strong short + recycles capital faster
        min_volume: float = 30_000.0,
        kelly_multiple: float = 0.25,
        max_open_stake: float | None = None,     # cap on total open exposure ($)
        max_new_per_cycle: int = 10,
    ) -> None:
        self.bankroll = bankroll
        self.band_lo, self.band_hi = band_lo, band_hi
        self.min_hours, self.max_hours = min_hours, max_hours
        self.min_volume = min_volume
        self.kelly_multiple = kelly_multiple
        self.max_open_stake = max_open_stake if max_open_stake is not None else bankroll
        self.max_new_per_cycle = max_new_per_cycle

    # ------------------------------------------------------------------

    def run_cycle(self, feed: DataFeed, store: PaperStore, notifier: PaperNotifier) -> CycleResult:
        settled = self._settle(feed, store, notifier)
        opps, opened = self._record(feed, store, notifier)
        store.log_scan(opps, opened)
        stats = store.stats()
        notifier.cycle_summary(opened, settled, stats)
        logger.info("paper_cycle_done", opportunities=opps, opened=opened,
                    settled_now=settled, open_bets=stats["open"],
                    realized_pnl=stats["realized_pnl"])
        return CycleResult(opportunities=opps, opened=opened, settled=settled, stats=stats)

    # -- settle ---------------------------------------------------------

    def _settle(self, feed: DataFeed, store: PaperStore, notifier: PaperNotifier) -> int:
        settled = 0
        for bet in store.open_bets():
            res = feed.get_resolution(bet.condition_id)
            if res is None or not res.closed:
                continue
            if res.winning_token_id is None:
                # resolved but no clean winner (void / 50-50) → refund
                store.settle_bet(bet.id, "VOID", bet.entry_price, 0.0)
                logger.info("paper_bet_void", bet_id=bet.id, slug=bet.slug)
                settled += 1
                continue
            won = bet.token_id == res.winning_token_id
            settle_price = 1.0 if won else 0.0
            pnl = round(bet.shares * settle_price - bet.stake_usd, 2)
            store.settle_bet(bet.id, "WON" if won else "LOST", settle_price, pnl)
            notifier.bet_settled(bet.question or bet.slug, bet.outcome, won, pnl)
            logger.info("paper_bet_settled", bet_id=bet.id, won=won, pnl=pnl, slug=bet.slug)
            settled += 1
        return settled

    # -- scan & record --------------------------------------------------

    def _record(self, feed: DataFeed, store: PaperStore, notifier: PaperNotifier) -> tuple[int, int]:
        opps = scan_live(
            feed, band_lo=self.band_lo, band_hi=self.band_hi,
            min_hours=self.min_hours, max_hours=self.max_hours,
            min_volume=self.min_volume, bankroll=self.bankroll,
            kelly_multiple=self.kelly_multiple,
        )
        open_stake = store.stats()["open_stake"]
        fill_floor = self.band_lo - 0.03
        opened = 0
        for o in opps:
            if opened >= self.max_new_per_cycle:
                break
            if store.has_open(o.condition_id):
                continue
            # verify real fill on the live book
            fq = analyze_depth(feed.fetch_order_book(o.token), o.suggested_stake, self.band_hi)
            if (fq.avg_fill_price is None or fq.filled_frac <= 0.99
                    or not (fill_floor <= fq.avg_fill_price <= self.band_hi)):
                continue
            if open_stake + o.suggested_stake > self.max_open_stake:
                continue
            entry = fq.avg_fill_price
            shares = round(o.suggested_stake / entry, 4)
            bet = Bet(
                id=None, condition_id=o.condition_id, token_id=o.token,
                slug=o.slug, question=o.question, outcome=o.outcome,
                entry_price=entry, stake_usd=o.suggested_stake, shares=shares,
                opened_at=datetime.now(timezone.utc).isoformat(),
                resolves_at=_resolves_at(o.hours_to_resolve),
            )
            if store.record_bet(bet) is not None:
                open_stake += o.suggested_stake
                opened += 1
                notifier.bet_opened(o.question or o.slug, o.outcome, entry,
                                    o.suggested_stake, o.hours_to_resolve)
                logger.info("paper_bet_opened", slug=o.slug, entry=entry,
                            stake=o.suggested_stake)
        return len(opps), opened


def _resolves_at(hours: float) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
