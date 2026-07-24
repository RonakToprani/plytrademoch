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

## 2. Favorite / longshot calibration — CANDIDATE EDGE FOUND

Question: is the market's own price mispriced enough to trade, no copying needed?

Method (`python -m backtest.run horizon`): neutral, volume-ranked universe of
resolved binary markets (Gamma closed-markets listing — real elections/sports/
crypto, not junk); price each market at a FIXED lead time before resolution (CLOB
price history) to avoid the convergence bias that inflates a naive `/trades`
pooling; score BOTH outcome tokens (scoring only token0 biases the curve — it's
the underdog side ~73% of the time); bucket by price; report realized win rate vs
price and buy-ROI after 1¢ slippage, with a per-bucket bootstrap CI.

Result (both tokens, ~750–900 markets/horizon, 24h/72h/168h all consistent):

| price band | win rate | mean price | buy ROI @1¢ | verdict |
|-----------|----------|-----------|-------------|---------|
| 0.10–0.20 | ~25–27%  | ~0.15     | **+48% to +66%, CI > 0** | **EDGE** |
| 0.30–0.70 | ≈ price  | —         | ~0         | calibrated |
| 0.80–0.90 | ~75%     | ~0.85     | −10% to −13%, CI < 0 | overpriced |
| <0.10, >0.90 | —      | —         | ~0 to negative | no edge |

- **The edge: buy the underdog at ~0.10–0.20.** Those tokens win ~25–27% of the
  time, not 15%. Its mirror — strong favorites (0.80–0.90) win only ~75%, not
  85% — is the *same markets' other side*. One coherent phenomenon: **market
  prices are too extreme; buy the underdog / fade the strong favorite.**
- **Robustness checks passed:** holds at all three horizons; survives both-token
  scoring (not a token0 artifact); the 0.10–0.20 bucket spans **104 distinct
  events across 108 markets** (29 wins from 28 different events — World Cup, NBA,
  geopolitics, crypto, esports), so it is **not** a correlated-election artifact;
  cost-robust (still strongly positive at 1¢, degrades slowly).
- The biased `/trades` "+22% favorites underpriced" was a timing artifact and is
  gone; favorites are calibrated-to-slightly-overpriced.

- **Time split PASSED.** Splitting at 2026-04-09 into two independent periods,
  the 0.10–0.20 underdog edge holds in both: EARLY (2023-05→2026-04) win 23.8%,
  +54% ROI; LATE (2026-04→2026-07) win 28.8%, +73% ROI. Favorites overpriced in
  both; midfield ≈ −(slippage) in both (a clean control). Not a regime artifact.

### Caveats still open before deploying capital
- **Negative skew.** ~27% win rate → you lose 73% of bets outright; returns come
  from occasional ~5–8× payoffs. Needs many small, uncorrelated bets and
  fractional-Kelly sizing; expect long losing streaks.
- **Liquidity/depth** at 0.10–0.20 is not modeled (flat slippage only). Must
  verify you can fill meaningful size without moving the price.
- **Low throughput.** With the resolution window applied (below), only a handful
  of qualifying markets exist at any moment — the book diversifies over weeks.

## 3. Strategy spec (from the validated edge) — `backtest.run live`

- **Signal:** buy the outcome token priced in **[0.10, 0.20]**.
- **Resolution window:** only markets resolving in **24h–168h** (the window the
  edge was measured in). This is critical — a naive scan without the upper bound
  surfaces 2028-election longshots 2 years out (correlated, capital-locking) that
  the backtest never validated. With the window, the scan returns near-term,
  diverse events (sports, geopolitics, crypto).
- **Liquidity:** volume ≥ $30k. **Diversify:** one bet per event.
- **Hold to resolution** (the edge is defined on resolution; no early exit).
- **Sizing:** fractional (¼) Kelly using the band's calibrated win rate (~0.27),
  NOT the market price — capped at 5% of bankroll, floored at $1.

`python -m backtest.run live --bankroll 150` prints today's opportunities with
suggested stakes. DRY-RUN / informational only.

### Next steps toward (paper) trading
1. Order-book depth check at the quoted price (can we fill the suggested size?).
2. Paper-trading loop: persist scanned bets, mark to resolution, track realized
   P&L vs the backtest expectation — reusing the existing DB / dashboard.
3. Only then, and only with the risk-manager bugs fixed (VPN debounce, daily-loss
   gate, DB pruning) + launchd supervision, consider small real capital.

## Reproduce
```bash
python -m backtest.run edge                 # copy-thesis test (rejected)
python -m backtest.run characterize         # wallet copyability (trade frequency)
python -m backtest.run horizon --max-markets 2000 --min-volume 30000   # calibration
python -m backtest.run live --bankroll 150  # today's underdog opportunities
```
