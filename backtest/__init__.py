"""
backtest/ — Edge-measurement harness for Polymarket strategies.

Purpose: judge any trading signal (starting with whale copy-trading) by the
same honest, cost-aware test against resolved-market ground truth, so we can
tell whether a strategy has real out-of-sample edge BEFORE risking capital —
paper or real.

Modules:
  • datafeed.py — fetch & cache whale activity + market resolutions (read-only
                  Data/Gamma APIs; no VPN or auth required).
  • edge.py     — score entries against resolution outcomes with a cost model,
                  and report edge with a bootstrap confidence interval.
  • run.py      — CLI: characterize wallets by copyability, run the edge test.

Nothing here places orders or touches the live bot DB.
"""
