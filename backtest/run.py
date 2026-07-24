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

from backtest.bias import calibrate
from backtest.datafeed import DataFeed
from backtest.edge import build_entries, slippage_sweep
from backtest.horizon import calibrate_at_horizon
from backtest.live import scan as scan_live

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


# ---------------------------------------------------------------------------
# bias — favorite/longshot calibration across a neutral market universe
# ---------------------------------------------------------------------------

def cmd_bias(args: argparse.Namespace) -> None:
    with DataFeed() as feed:
        print(f"fetching resolved-market universe (min_volume=${args.min_volume:,.0f}, "
              f"max={args.max_markets}) ...")
        universe = feed.fetch_resolved_universe(
            max_markets=args.max_markets, min_volume=args.min_volume, refresh=args.refresh
        )
        print(f"universe: {len(universe)} resolved binary markets\n"
              f"pooling neutral BUY prints (this is cached after first run) ...")
        res = calibrate(
            feed, universe,
            slippage=args.slippage, bucket_width=args.bucket_width,
            trades_per_market=args.trades_per_market, progress=True,
        )
        print(f"\n=== Calibration: {res.n_prints:,} BUY prints across "
              f"{res.n_markets} markets | slippage {res.slippage:.3f} ===")
        print(f"  {'price band':>12} {'n':>8} {'mean px':>8} {'win rate':>9} "
              f"{'gap':>8} {'buy ROI':>9}  interpretation")
        for b in res.buckets:
            if b.n == 0:
                continue
            interp = ("underpriced" if b.gap > 0.02 else
                      "overpriced" if b.gap < -0.02 else "calibrated")
            print(f"  {b.lo:>5.2f}-{b.hi:<5.2f} {b.n:>8,} {b.mean_price:>8.3f} "
                  f"{b.win_rate:>8.1%} {b.gap:>+7.1%} {b.mean_roi:>+8.1%}  {interp}")
        print("\n  gap = realized win rate - mean price. "
              "Positive = favorites cheap; negative = longshots dear.")
        print("  buy ROI is net of slippage, held to resolution. "
              "A tradeable edge needs buy ROI > 0 after slippage.")
        print("  ⚠️  TIMING BIAS: /trades over-samples fills near resolution, which "
              "OVERSTATES the favorite edge.\n     Use `horizon` for the honest, "
              "fixed-lead-time measurement before trusting these numbers.")


def cmd_horizon(args: argparse.Namespace) -> None:
    with DataFeed() as feed:
        print(f"fetching resolved-market universe (min_volume=${args.min_volume:,.0f}, "
              f"max={args.max_markets}) ...")
        universe = feed.fetch_resolved_universe(
            max_markets=args.max_markets, min_volume=args.min_volume, refresh=args.refresh
        )
        print(f"universe: {len(universe)} resolved binary markets")
        for hz in args.horizons:
            print(f"\npricing each market {hz}h before resolution (cached after first run) ...")
            res = calibrate_at_horizon(
                feed, universe, horizon_hours=hz, slippage=args.slippage,
                bucket_width=args.bucket_width, progress=True,
            )
            print(f"\n=== Ex-ante calibration @ {hz}h before resolution | "
                  f"{res.n_markets} markets priced ({res.n_skipped} skipped) | "
                  f"slippage {res.slippage:.3f} ===")
            print(f"  {'price band':>12} {'n':>6} {'mean px':>8} {'win rate':>9} "
                  f"{'gap':>8} {'buy ROI':>9} {'95% CI (ROI)':>20}  verdict")
            for b in res.buckets:
                if b.n == 0:
                    continue
                lo, hi = b.roi_ci()
                # A real edge = ROI CI entirely above 0 with a meaningful sample.
                if b.n < 20:
                    verdict = "thin"
                elif lo > 0:
                    verdict = "EDGE"
                elif hi < 0:
                    verdict = "lose"
                else:
                    verdict = "flat"
                ci = "  n<5" if lo == float("-inf") else f"[{lo:>+6.1%},{hi:>+6.1%}]"
                print(f"  {b.lo:>5.2f}-{b.hi:<5.2f} {b.n:>6,} {b.mean_price:>8.3f} "
                      f"{b.win_rate:>8.1%} {b.gap:>+7.1%} {b.mean_roi:>+8.1%} {ci:>20}  {verdict}")
        print("\n  gap = realized win rate - mean price (ex-ante). "
              "buy ROI is net of slippage, held to resolution.")
        print("  verdict EDGE = ROI 95% CI entirely > 0 with n>=20; 'thin' = too few markets.")


def cmd_live(args: argparse.Namespace) -> None:
    with DataFeed() as feed:
        print(f"scanning open markets for underdogs in [{args.band_lo:.2f}, "
              f"{args.band_hi:.2f}] resolving >= {args.min_hours:.0f}h out, "
              f"volume >= ${args.min_volume:,.0f} ...")
        opps = scan_live(
            feed, band_lo=args.band_lo, band_hi=args.band_hi,
            min_hours=args.min_hours, max_hours=args.max_hours,
            min_volume=args.min_volume, bankroll=args.bankroll,
            kelly_multiple=args.kelly,
        )
        if not opps:
            print("no opportunities right now.")
            return
        shown = opps[: args.top]
        total = sum(o.suggested_stake for o in shown)
        print(f"\n{len(opps)} opportunities (one per event). Top {len(shown)} "
              f"by liquidity — suggested book ${total:.0f} on ${args.bankroll:.0f} bankroll "
              f"({args.kelly:.0%} Kelly):\n")
        if args.depth:
            print("  checking live order-book depth for each ...\n")
            from backtest.depth import analyze as analyze_depth
            print(f"  {'mid':>4} {'ask':>4} {'fill':>5} {'stake':>6} {'cap@band':>9} "
                  f"{'hrs':>4}  market")
            tradeable = 0
            # A real fill must land inside the edge band (with a small tolerance
            # below), fill the stake, and not be a stale/dust book (ask ~0).
            fill_floor = args.band_lo - 0.03
            for o in shown:
                fq = analyze_depth(feed.fetch_order_book(o.token), o.suggested_stake, args.band_hi)
                ask = f"{fq.best_ask:.2f}" if fq.best_ask is not None else "  - "
                fill = f"{fq.avg_fill_price:.3f}" if fq.avg_fill_price is not None else "  -  "
                ok = (fq.avg_fill_price is not None and fq.filled_frac > 0.99
                      and fill_floor <= fq.avg_fill_price <= args.band_hi)
                if fq.best_ask is not None and fq.best_ask < fill_floor:
                    flag = "  <-- stale/dust book (skip)"
                elif fq.best_ask is not None and fq.best_ask > args.band_hi:
                    flag = "  <-- ask out of band"
                elif fq.filled_frac <= 0.99:
                    flag = "  <-- too thin for stake"
                else:
                    flag = ""
                tradeable += int(ok)
                print(f"  {o.price:>4.2f} {ask:>4} {fill:>5} ${o.suggested_stake:>5.2f} "
                      f"${fq.capacity_in_band:>8,.0f} {o.hours_to_resolve:>4.0f}  "
                      f"{(o.question or o.slug)[:44]} [{o.outcome}]{flag}")
            print(f"\n  {tradeable}/{len(shown)} genuinely fillable in-band at the suggested stake.")
            print("  mid=Gamma price, ask=best executable buy, fill=VWAP for the stake, "
                  "cap@band=$ available at asks <= band-hi.")
        else:
            print(f"  {'price':>5} {'~win':>5} {'stake':>6} {'hrs':>5} {'vol':>10}  market")
            for o in shown:
                print(f"  {o.price:>5.2f} {o.est_win_rate:>5.0%} ${o.suggested_stake:>5.2f} "
                      f"{o.hours_to_resolve:>5.0f} ${o.volume:>9,.0f}  "
                      f"{(o.question or o.slug)[:52]}  [{o.outcome}]")
        print("\n  DRY-RUN / informational only — no orders placed. Edge is at the band "
              "level; size small and diversified (negative skew, ~27% win rate).")


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

    pb = sub.add_parser("bias", help="favorite/longshot calibration (neutral universe)")
    pb.add_argument("--max-markets", type=int, default=1_000)
    pb.add_argument("--min-volume", type=float, default=5_000.0)
    pb.add_argument("--trades-per-market", type=int, default=500)
    pb.add_argument("--slippage", type=float, default=0.01)
    pb.add_argument("--bucket-width", type=float, default=0.10)
    pb.add_argument("--refresh", action="store_true")
    pb.set_defaults(func=cmd_bias)

    ph = sub.add_parser("horizon", help="honest ex-ante calibration at a fixed lead time")
    ph.add_argument("--max-markets", type=int, default=1_000)
    ph.add_argument("--min-volume", type=float, default=5_000.0)
    ph.add_argument("--horizons", type=int, nargs="+", default=[24, 72, 168],
                    help="hours before resolution to price at (default 24 72 168)")
    ph.add_argument("--slippage", type=float, default=0.01)
    ph.add_argument("--bucket-width", type=float, default=0.10)
    ph.add_argument("--refresh", action="store_true")
    ph.set_defaults(func=cmd_horizon)

    pl = sub.add_parser("live", help="scan open markets for underdog opportunities (DRY-RUN)")
    pl.add_argument("--band-lo", type=float, default=0.10)
    pl.add_argument("--band-hi", type=float, default=0.20)
    pl.add_argument("--min-hours", type=float, default=24.0)
    pl.add_argument("--max-hours", type=float, default=168.0,
                    help="only markets resolving within this many hours (validated window)")
    pl.add_argument("--min-volume", type=float, default=30_000.0)
    pl.add_argument("--bankroll", type=float, default=100.0)
    pl.add_argument("--kelly", type=float, default=0.25, help="Kelly multiple (0.25 = quarter)")
    pl.add_argument("--top", type=int, default=25)
    pl.add_argument("--depth", action="store_true",
                    help="check live order-book depth / real fill price per opportunity")
    pl.set_defaults(func=cmd_live)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
