"""
paper/run.py — CLI for the underdog paper-trading system.

    python -m paper.run cycle          # settle resolved + record new bets (one pass)
    python -m paper.run stats          # print the book + running P&L
    python -m paper.run telegram-test  # send a test Telegram message
    python -m paper.run dashboard      # launch the one-page monitor (localhost:8060)

Run `cycle` on a schedule (launchd/cron, e.g. hourly). DRY-RUN — no real orders.
"""

from __future__ import annotations

import argparse

from backtest.datafeed import DataFeed
from paper.engine import PaperTrader
from paper.notify import PaperNotifier
from paper.store import PaperStore


def cmd_cycle(args: argparse.Namespace) -> None:
    store = PaperStore()
    notifier = PaperNotifier()
    trader = PaperTrader(bankroll=args.bankroll, kelly_multiple=args.kelly,
                         min_volume=args.min_volume, max_new_per_cycle=args.max_new)
    with DataFeed() as feed:
        res = trader.run_cycle(feed, store, notifier)
    s = res.stats
    print(f"cycle: {res.opportunities} opportunities → +{res.opened} opened, "
          f"{res.settled} settled")
    print(f"book: {s['open']} open (${s['open_stake']:.0f}) | {s['settled']} settled | "
          f"realized P&L ${s['realized_pnl']:.2f} | win {s['win_rate']*100:.0f}% | "
          f"ROI {s['roi']*100:+.0f}%")
    if not notifier.enabled:
        print("(telegram disabled — set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID in .env)")
    store.close()


def cmd_stats(args: argparse.Namespace) -> None:
    store = PaperStore()
    s = store.stats()
    print(f"=== Paper book ({s['total']} bets) ===")
    print(f"  open:     {s['open']}  (${s['open_stake']:.2f} exposure)")
    print(f"  settled:  {s['settled']}  (won {s['won']}, lost {s['lost']})")
    print(f"  win rate: {s['win_rate']*100:.1f}%  (backtest expectation ~27%)")
    print(f"  realized: ${s['realized_pnl']:.2f} on ${s['settled_stake']:.2f} staked  "
          f"→ ROI {s['roi']*100:+.1f}%  (backtest expectation +50–70%)")
    print(f"  last scan: {store.last_scan() or 'never'}")
    open_bets = store.open_bets()
    if open_bets:
        print("\n  open positions:")
        for b in open_bets[:30]:
            print(f"   {b.entry_price:>5.3f} ${b.stake_usd:>5.2f}  "
                  f"{(b.question or b.slug)[:52]} [{b.outcome}]")
    store.close()


def cmd_telegram_test(args: argparse.Namespace) -> None:
    n = PaperNotifier()
    if not n.enabled:
        print("telegram not configured — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return
    ok = n.send("✅ <b>Underdog paper bot</b> — Telegram is live. "
                "You'll get alerts on bets opened, settled, and cycle summaries.")
    print("sent ✓" if ok else "send failed — check token/chat id")


def cmd_review(args: argparse.Namespace) -> None:
    from paper.review import run_review
    report = run_review(send=not args.no_telegram)
    print(report)


def cmd_dashboard(args: argparse.Namespace) -> None:
    from paper.dashboard import create_app
    app = create_app()
    print(f"dashboard → http://localhost:{args.port}")
    app.run(host="0.0.0.0", port=args.port, debug=False)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="paper.run", description="Underdog paper trading")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("cycle", help="settle + record one pass")
    pc.add_argument("--bankroll", type=float, default=150.0)
    pc.add_argument("--kelly", type=float, default=0.25)
    pc.add_argument("--min-volume", type=float, default=30_000.0)
    pc.add_argument("--max-new", type=int, default=10)
    pc.set_defaults(func=cmd_cycle)

    ps = sub.add_parser("stats", help="print the book + P&L")
    ps.set_defaults(func=cmd_stats)

    pt = sub.add_parser("telegram-test", help="send a test Telegram message")
    pt.set_defaults(func=cmd_telegram_test)

    pr = sub.add_parser("review", help="nightly strategy review + recommendations")
    pr.add_argument("--no-telegram", action="store_true", help="don't send the summary")
    pr.set_defaults(func=cmd_review)

    pd = sub.add_parser("dashboard", help="launch the one-page monitor")
    pd.add_argument("--port", type=int, default=8060)
    pd.set_defaults(func=cmd_dashboard)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
