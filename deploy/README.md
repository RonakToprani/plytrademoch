# Deployment (launchd, always-on Mac)

Two launchd agents supervise the paper strategy. The plists here are the live
config (absolute paths for this machine — adjust paths if the repo moves).

| Agent | What | Schedule |
|-------|------|----------|
| `com.underdog.cycle` | `paper.run cycle` — settle resolved + record new bets | every 30 min + at load |
| `com.underdog.dashboard` | `paper.run dashboard` — POLY TRADING monitor on :8060 | always up (KeepAlive) |
| `com.underdog.review` | `paper.run review` — grade the book + edge-by-band + recommendations, to Telegram | daily 20:00 local |

Dashboard: **http://<lan-ip>:8060** (e.g. http://10.0.0.79:8060).

## Install / update

```bash
cp deploy/com.underdog.*.plist ~/Library/LaunchAgents/
UID_=$(id -u)
for l in com.underdog.cycle com.underdog.dashboard; do
  launchctl bootout   gui/$UID_/$l 2>/dev/null
  launchctl bootstrap gui/$UID_ ~/Library/LaunchAgents/$l.plist
done
# after editing dashboard code, reload it:
launchctl kickstart -k gui/$UID_/com.underdog.dashboard
```

## Observe / control

```bash
launchctl list | grep underdog          # status 0 = last run clean
tail -f logs/cycle.log                   # scan/settle activity
tail -f logs/dashboard.log               # web server
launchctl bootout gui/$(id -u)/com.underdog.cycle   # stop the loop
```

Timeframes (tuned for the edge): buy 0.10–0.20 underdogs resolving in **24–96h**
(edge is as strong short + recycles capital faster), scan every **30 min**.
Set `POLY_BANKROLL` env to change the bankroll the dashboard displays.
