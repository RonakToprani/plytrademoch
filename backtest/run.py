"""
backtest/run.py — CLI for the edge-measurement harness.

Examples:
    # Characterize every tracked wallet by copyability (trade frequency):
    python -m backtest.run characterize

    # Run the copy-edge test on the tracked wallets (with slippage sweep):
    python -m backtest.run edge

    # Test specific wallets, fetching deeper history:
    python -m backtest.run edge --wallets 0x0b9c...,0xee00... --max-rows 20000

Reads the tracked-wallet list from the live bot DB (read-only) unless --wallets
is given. Never places orders; never writes to the bot DB.
"""

from __future__ import annotations

import argparse
import sqlite3
import statistics
import sys

from backtest.datafeed import DataFeed
from backtest.edge import build_entries, slippage_sweep

_BOT_DB = "polymarket_bot.db"


def _tracked_wallets() -> list[tuple[str, str]]:
    """Return (address, label) for wallets in the live bot DB, best score first."""
    try:
        db = sqlite3.connect(f"file:{_BOT_DB}?mode=ro", uri=True)
        rows = db.execute(
            "SELECT address, lifetime_pnl, win_rate FROM tracked_wallets ORDER BY score DESC"
        ).fetchall()
        db.close()
    except sqlite3.Error as exc:
        print(f"could not read {_BOT_DB}: {exc}", file=sys.stderr)
        return []
    return [(a, f"pnl${p/1e3:.0f}k wr{w:.2f}") for a, p, w in rows]


def _resolve_wallets(args: argparse.Namespace) -> list[tuple[str, str]]:
    if args.wallets:
        return [(w.strip().lower(), "cli") for w in args.wallets.split(",") if w.strip()]
    return _tracked_wallets()


# ---------------------------------------------------------------------------
# characterize — trade frequency = the copyability screen
# ---------------------------------------------------------------------------

def cmd_characterize(args: argparse.Namespace) -> None:
    wallets = _resolve_wallets(args)
    if not wallets:
        print("no wallets to characterize.")
        return

    print(f"{'wallet':<12} {'label':<18} {'trades':>7} {'trades/day':>10} "
          f"{'med_gap_s':>10} {'copyable?':>10}")
    with DataFeed() as feed:
        for addr, label in wallets:
            trades = feed.fetch_activity(addr, max_rows=args.max_rows, refresh=args.refresh)
            trades = [t for t in trades if t.side == "BUY"]
            if len(trades) < 5:
                print(f"{addr[:10]:<12} {label:<18} {len(trades):>7}  (too few)")
                continue
            ts = sorted(t.ts for t in trades)
            span = ts[-1] - ts[0]
            gaps = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]
            med_gap = statistics.median(gaps)
            tpd = len(trades) / (span / 86_400) if span > 0 else float("inf")
            # Heuristic: copyable if it trades slowly enough that 30-60s latency
            # doesn't dominate — i.e. well under ~50 BUYs/day.
            copyable = "yes" if tpd < 50 else ("marginal" if tpd < 150 else "NO-hft")
            print(f"{addr[:10]:<12} {label:<18} {len(trades):>7} {tpd:>10.0f} "
                  f"{med_gap:>10.0f} {copyable:>10}")


# ---------------------------------------------------------------------------
# edge — the go / no-go test
# ---------------------------------------------------------------------------

def cmd_edge(args: argparse.Namespace) -> None:
    wallets = _resolve_wallets(args)
    if not wallets:
        print("no wallets to test.")
        return

    with DataFeed() as feed:
        for addr, label in wallets:
            trades = feed.fetch_activity(addr, max_rows=args.max_rows, refresh=args.refresh)
            entries = build_entries(trades)
            results = slippage_sweep(
                entries, feed,
                min_price=args.min_price, max_price=args.max_price,
            )
            base = results[0]
            print(f"\n=== {addr[:12]}  {label} ===")
            print(f"  BUY signals: {base.total_signals} | on resolved markets: "
                  f"{base.n_resolved} | scored (in {args.min_price}-{args.max_price} band): "
                  f"{base.n_entries}")
            if base.n_entries < 10:
                print("  too few resolved entries to judge edge "
                      "(fetch deeper history with --max-rows).")
                continue
            print(f"  win rate: {base.win_rate:.1%} | avg entry px: {base.avg_entry_price:.3f}")
            print(f"  {'slippage':>9} {'mean ROI/bet':>13} {'95% CI':>22} "
                  f"{'notional ROI':>13} {'verdict':>8}")
            for r in results:
                lo, hi = r.roi_ci
                verdict = "EDGE" if lo > 0 else ("flat" if hi > 0 else "no")
                print(f"  {r.slippage:>9.3f} {r.mean_roi:>12.1%} "
                      f"  [{lo:>+6.1%}, {hi:>+6.1%}] {r.notional_roi:>12.1%} {verdict:>8}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="backtest.run", description="Polymarket edge harness")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--wallets", help="comma-separated addresses (default: tracked wallets)")
    common.add_argument("--max-rows", type=int, default=5_000, help="max activity rows to fetch/wallet")
    common.add_argument("--refresh", action="store_true", help="force re-fetch, ignore cache")

    pc = sub.add_parser("characterize", parents=[common], help="screen wallets by trade frequency")
    pc.set_defaults(func=cmd_characterize)

    pe = sub.add_parser("edge", parents=[common], help="run the copy-edge test")
    pe.add_argument("--min-price", type=float, default=0.08)
    pe.add_argument("--max-price", type=float, default=0.92)
    pe.set_defaults(func=cmd_edge)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
