"""
paper/ — Paper-trading the validated underdog edge (DRY-RUN, no real orders).

Runs the `backtest.live` scan on a schedule, records the bets it *would* place at
the real order-book fill price, marks them to resolution, and tracks realized P&L
against the backtest expectation (~+17% ROI, ~24.5% win rate). Sends spam-free
Telegram alerts and feeds a simple one-page dashboard.

Self-contained: its own SQLite (`paper_underdog.db`), never touches the old
copy-trading DB. Places no orders, ever.
"""
