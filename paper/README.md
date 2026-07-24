# Underdog paper trading

Paper-trades the validated underdog edge (buy 0.10–0.20, resolving 24–168h out;
see `../backtest/FINDINGS.md`). DRY-RUN — records the bets it *would* place at the
real order-book fill price, settles them at resolution, tracks P&L vs the backtest
expectation. Places no orders. Own DB (`paper_underdog.db`); never touches the old
copy-trading DB.

## Use

```bash
# One pass: settle resolved bets, then scan + record new ones. Schedule this
# (launchd/cron) hourly. Idempotent — safe to run repeatedly.
python -m paper.run cycle --bankroll 150

# See the book + running P&L:
python -m paper.run stats

# Live one-page monitor → http://localhost:8060
python -m paper.run dashboard

# Verify Telegram is wired (uses TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID from .env):
python -m paper.run telegram-test
```

## How a cycle works

1. **Settle** every OPEN bet whose market has resolved (CLOB winner flag) →
   $1 win / $0 loss, realized P&L booked.
2. **Scan** open markets for underdogs (`backtest.live`), **verify depth** on the
   live book (`backtest.depth`), and record a paper bet at the real VWAP fill —
   one per market, capped by total open exposure (default = bankroll).

## Telegram (spam-free)

Event-driven only — fires on a bet opened, a bet settled, and a non-empty cycle
summary. It never polls, so it can't spam the way the old VPN check did.

## Watch for

The strategy is **negative-skew**: ~27% win rate, returns from occasional 5–8×
payoffs. Expect long losing streaks; judge it on realized ROI over many settled
bets (dozens+), not the first handful.
