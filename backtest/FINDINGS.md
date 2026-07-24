# Findings — Polymarket edge investigation

Living record of what the `backtest/` harness has actually proven. Every number
here is reproducible from the CLI on read-only public data (no VPN/auth).

## 1. Copy-trading thesis — REJECTED

The original plan: follow wallets with $100k+ lifetime P&L and >65% win rate,
copy their entries at 30s poll latency.

Tested by replaying each whale BUY, held to resolution, cost-adjusted
(`python -m backtest.run edge`). Across all 7 tracked wallets:

- **Top-P&L whales are HFT market-makers** — up to ~21,000 trades/day, ~2s
  between trades. Uncopyable at 30s latency by construction.
- **Wallets passing the win-rate filter lose when their entries are held to
  resolution.** The scanner's "0.78 win rate" whale actually wins 26% of its
  entries (it buys longshots), −45% ROI/bet at zero slippage.
- **`0x507e` is the instructive trap:** +53% equal-weighted ROI (73.7% win) but
  −7% to −14% **notional-weighted** — it wins small and loses big. A naive
  win-rate or equal-weight backtest would have sent capital live on it.

Conclusion: whale edge lives in exit timing, bet sizing, and HFT — none copyable
by a slow home-server bot. **Do not resume copy-trading these wallets.**

## 2. Favorite / longshot calibration — IN PROGRESS

Question: is the market's own price mispriced enough to trade, no copying needed?

Method (`python -m backtest.run horizon`): take a neutral, volume-ranked universe
of resolved binary markets (Gamma closed-markets listing — real elections/sports/
crypto, not auto-generated junk); price each market at a FIXED lead time before
resolution (CLOB price history) to avoid the convergence bias that inflates a
naive `/trades` pooling; bucket by price; measure realized win rate vs price and
buy-ROI after slippage, with a per-bucket bootstrap CI.

Status / current read (large sample, both outcome tokens scored):
- **Favorites (price 0.5–1.0) are essentially calibrated** — no significant edge.
  The "+22% favorites underpriced" from the biased `/trades` method was a timing
  artifact and disappears under the honest horizon method.
- **Signal concentrated in moderate longshots (~0.10–0.30):** they appear to win
  somewhat more often than their price implies. Whether this survives as a
  *tradeable* edge is not yet settled — see caveats.

### Open caveats before trusting the longshot signal
- **Correlated multi-candidate events.** Volume-ranked universe is heavy on
  election markets where many candidate sub-markets are mutually exclusive; the
  bootstrap CI assumes independence and will overstate significance. Needs
  event-level dedup or a cluster bootstrap.
- **Negative skew / capital efficiency.** Literature puts the real favorite-
  longshot edge at only ~2–5%/contract, with big drawdowns; a longshot strategy
  wins rarely and large, which is hard to size.
- **Liquidity/depth** at the quoted price is not modeled — only a flat slippage.
- **Time robustness** (does the edge hold out-of-sample across periods?) not yet
  split.

Next: event-dedup, category split (sports vs politics vs crypto), and a
train/test time split before any paper deployment.

## Reproduce
```bash
python -m backtest.run edge                 # copy-thesis test
python -m backtest.run characterize         # wallet copyability (trade frequency)
python -m backtest.run horizon --max-markets 2000 --min-volume 30000
```
