# Backtest / edge-measurement harness

Judge any Polymarket signal by one honest, cost-aware test **before** risking
capital (paper or real): does it have real out-of-sample edge?

The harness is read-only. It uses only public endpoints (Data API `/activity`,
CLOB `/markets/{condition_id}`), needs **no VPN and no API key**, places no
orders, and never writes to the live bot DB. Fetched data is cached in
`backtest_cache.db` (gitignored) so repeat runs are instant.

## The test

A whale BUYs an outcome token at price `p`. A copy bot sees it seconds later,
crosses the spread (the whale's own buy already moved the price), and can't match
the whale's exit — so it holds to resolution. The market settles $1 / $0.

    return on $1 staked = (1 / (p + slippage)) - 1   if the bought token won
                        = -1                          if it lost

Averaging that across many resolved entries measures edge after costs. A
bootstrap CI says whether it's distinguishable from zero; a **slippage sweep**
says how much execution cost the edge survives — the real go / no-go number.

Resolution ground truth comes from CLOB `/markets/{condition_id}`, which flags
the winning token directly (Gamma's `condition_id` filter is unreliable — it
silently returns unrelated markets).

## Usage

```bash
# Screen tracked wallets by copyability (trade frequency):
python -m backtest.run characterize

# Run the copy-edge test with a slippage sweep:
python -m backtest.run edge

# Specific wallets / deeper history:
python -m backtest.run edge --wallets 0xabc...,0xdef... --max-rows 5000
```

Wallets default to the tracked set in `polymarket_bot.db` (read-only).

## Favorite / longshot calibration (strategy #2 candidate)

Is the market's price itself mispriced — longshots overpriced, favorites cheap?
Two commands, on a **neutral** universe of resolved markets (Gamma closed-markets
listing), not whale-selected:

```bash
# Honest, ex-ante: price each market at a FIXED lead time before resolution
# (CLOB price history), then bucket by price. This is the one to trust.
python -m backtest.run horizon --min-volume 30000 --max-markets 1500 --horizons 24 72 168

# Fast but BIASED first look: pools /trades fills, which cluster near resolution
# and overstate the favorite edge. Kept only for contrast.
python -m backtest.run bias --min-volume 20000 --max-markets 500
```

Read the `gap` column (realized win rate − mean price) and `buy ROI` (net of
slippage, held to resolution). A tradeable edge needs `buy ROI > 0` after
slippage in a bucket with enough markets to be significant. The published
Polymarket favorite-longshot edge is small (~2–5%/contract), so treat any
large number as a bias artifact until the sample is big and horizon-controlled.

## Known limits (read before trusting a number)

- **Hold-to-resolution ignores whale exits.** If a whale's edge is in cutting
  losers / taking profit early, this test won't credit it — but that edge isn't
  copyable at 30s latency anyway, which is the point.
- **Each BUY is one entry.** A whale scaling into a position generates several
  entries; equal-weighted ROI over-weights markets they re-trade. The
  notional-weighted ROI (dollar-weighted by the whale's own size) is the
  correction to read alongside it.
- **`/activity` pages back ~5000 rows** per wallet, so the sample is the wallet's
  most recent history, not its whole life.
- Slippage is a flat assumption, not a modeled order book. The sweep is there so
  you judge across a range rather than trusting one value.
