# Deployment (launchd, always-on Mac)

Five launchd agents supervise the paper strategy. The plists here are the live
config (absolute paths for this machine — adjust paths if the repo moves).

| Agent | What | Schedule |
|-------|------|----------|
| `com.underdog.cycle` | `paper.run cycle` — settle resolved + record new bets | every 30 min + at load |
| `com.underdog.dashboard` | `paper.run dashboard` — POLY TRADING monitor on :8060 | always up (KeepAlive) |
| `com.underdog.export` | `deploy/export_and_push.py` — push `reports/state.md` to main for the cloud Opus reviewer | every 3 h |
| `com.underdog.inbox` | `paper.run inbox` — archive Telegram messages sent to the bot into `reports/inbox/` | every 10 min |
| `com.underdog.review` | `paper.run review` — local rule-based grade of the book + edge-by-band, to Telegram | daily 20:00 local |

`review` overlaps with the cloud reviewer that `export` feeds — the two grade the
same book by different means. Run one or the other; bootstrap `review` only if
you want the local Telegram digest as well.

Dashboard: **http://<lan-ip>:8060** (e.g. http://10.0.0.79:8060).

## Install / update

```bash
cp deploy/com.underdog.*.plist ~/Library/LaunchAgents/
UID_=$(id -u)
for l in com.underdog.cycle com.underdog.dashboard com.underdog.export com.underdog.inbox; do
  launchctl bootout   gui/$UID_/$l 2>/dev/null
  launchctl bootstrap gui/$UID_ ~/Library/LaunchAgents/$l.plist
done
# optional local nightly digest (see note above):
# launchctl bootstrap gui/$UID_ ~/Library/LaunchAgents/com.underdog.review.plist
# after editing dashboard code, reload it:
launchctl kickstart -k gui/$UID_/com.underdog.dashboard
```

## Required: disable sleep

`StartInterval` agents **do not fire during macOS dark wake**. If the Mac sleeps,
`cycle` silently stops trading while the dashboard keeps answering HTTP 200 (a
resident process that dark wakes revive) and `launchctl list` keeps showing
`last exit code = 0`. Nothing looks wrong. A 21.5 h / ~43-cycle gap happened this
way on 2026-07-25.

```bash
sudo pmset -a sleep 0 disablesleep 1
```

## Observe / control

```bash
bash check_status.sh                     # full health check; exit 1 if unhealthy
bash check_status.sh --quiet             # only problems — use this for alerting
tail -f logs/cycle.log                   # scan/settle activity
launchctl kickstart -k gui/$(id -u)/com.underdog.cycle   # force a cycle now
launchctl bootout gui/$(id -u)/com.underdog.cycle        # stop the loop
```

Do **not** treat a live dashboard or `launchctl list` as a liveness check — use
`check_status.sh`, which compares the `logs/cycle.log` mtime against now.

Timeframes (tuned for the edge): buy **0.15–0.30** underdogs resolving in
**6–168h**, scan every **30 min**, $1,000 paper bankroll. Set from a 356k-market
/ 219k-event event-clustered calibration: 0.15–0.30 returns **+15.7%**
[+12.5, +18.9] with the `mention-count` and `fed-macro` segments excluded.
Both the band ceiling (0.25 -> 0.30) and the window ceiling (96h -> 168h) were
widened for **flow**, not ROI — the scan was finding only 2 tradeable events and
the book sat on 4% of its capital. Every price slice to 0.30 and every horizon to
168h is significantly positive; 0.33+ is dead.

Bankroll lives in THREE places and they must agree: `--bankroll` in
`com.underdog.cycle.plist`, `PaperTrader(bankroll=...)`, and `POLY_BANKROLL`
(or the default in `paper/dashboard.py`) for the dashboard's "% deployed" gauge.

## Telegram inbox (getting Claude recs onto this machine)

The Bot API **cannot return messages the bot itself sent** — `getUpdates` is
inbound-only. So a rec that Plykodobot delivered to you is not retrievable after
the fact. What *is* retrievable is anything sent or **forwarded to** the bot.

Forward a Claude rec to **@Plykodobot** and within 10 minutes it lands in
`reports/inbox/<date>-<id>-<slug>.md` and the `inbox` table, where an agent
working in this repo can read it:

```bash
python -m paper.run inbox              # poll now + list
python -m paper.run inbox --list-only  # just show what's archived
```

`reports/` is gitignored apart from `state.md`, so archived messages stay local
and are never pushed to GitHub. Telegram discards un-acknowledged updates after
~24h — that is the only real deadline, and the 10-minute schedule covers it.
