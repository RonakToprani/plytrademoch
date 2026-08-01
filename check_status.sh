#!/bin/bash
# Health check for the underdog paper-trading system.
#
#   bash check_status.sh          # full report
#   bash check_status.sh --quiet  # only problems (good for cron/alerting)
#
# Exit 0 = everything healthy, 1 = at least one FAIL.
#
# The point of this script: a live dashboard proves nothing. The dashboard is a
# resident process that macOS dark-wakes revive to serve HTTP, so it keeps
# answering 200 while the interval-driven cycle job is frozen. `launchctl list`
# is no better — a stalled job still shows "last exit code = 0". The only honest
# liveness signal is how long ago logs/cycle.log was last written.

cd "$(dirname "$0")" || exit 1

DB=paper_underdog.db
UID_NUM=$(id -u)
PORT=8060
CYCLE_MAX_AGE=2400      # 40 min (job runs every 30) — older means it stopped firing
EXPORT_MAX_AGE=14400    # 4 h    (job runs every 3 h)

QUIET=0
[ "$1" = "--quiet" ] && QUIET=1

FAILS=0
WARNS=0

say()  { [ "$QUIET" -eq 1 ] || printf '%s\n' "$*"; }
ok()   { [ "$QUIET" -eq 1 ] || printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; WARNS=$((WARNS+1)); }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; FAILS=$((FAILS+1)); }

# Human-readable age of a file, plus a FAIL/OK verdict against a max age.
age_of() {  # age_of <file> -> seconds, or empty if missing
    [ -f "$1" ] || return 1
    echo $(( $(date +%s) - $(stat -f "%m" "$1") ))
}
pretty_age() {
    local s=$1
    if   [ "$s" -lt 3600 ]  ; then echo "$((s/60))m ago"
    elif [ "$s" -lt 86400 ] ; then echo "$((s/3600))h $((s%3600/60))m ago"
    else                           echo "$((s/86400))d $((s%86400/3600))h ago"
    fi
}

say "========================================"
say "  UNDERDOG PAPER BOT — HEALTH CHECK"
say "  $(date)"
say "========================================"

# ---------------------------------------------------------------- launchd jobs
say ""
say "=== LAUNCHD JOBS ==="
for job in cycle export review dashboard inbox; do
    if launchctl print "gui/$UID_NUM/com.underdog.$job" >/dev/null 2>&1; then
        ok "com.underdog.$job loaded"
    else
        bad "com.underdog.$job NOT LOADED — launchctl bootstrap gui/$UID_NUM ~/Library/LaunchAgents/com.underdog.$job.plist"
    fi
done

# ------------------------------------------------------- the real liveness test
say ""
say "=== CYCLE FRESHNESS (the one that matters) ==="
if AGE=$(age_of logs/cycle.log); then
    if [ "$AGE" -gt "$CYCLE_MAX_AGE" ]; then
        bad "cycle.log last written $(pretty_age "$AGE") — BOT IS NOT TRADING"
        say "      fix: launchctl kickstart -k gui/$UID_NUM/com.underdog.cycle"
        say "      cause is usually sleep; see the SLEEP GUARD section below"
    else
        ok "cycle.log written $(pretty_age "$AGE")"
    fi
    say "  last: $(grep -E 'paper_cycle_done' logs/cycle.log | tail -1 | cut -c1-100)"
else
    bad "logs/cycle.log missing — the cycle job has never run"
fi

# --------------------------------------------------------------- dashboard
say ""
say "=== DASHBOARD ==="
DASH_PID=$(pgrep -f "paper.run dashboard" | head -1)
if [ -n "$DASH_PID" ]; then
    ok "process alive — PID $DASH_PID — up $(ps -o etime= -p "$DASH_PID" | xargs)"
else
    bad "dashboard process not running"
fi
CODE=$(curl -s -o /dev/null -m 5 -w "%{http_code}" "http://localhost:$PORT/" 2>/dev/null)
if [ "$CODE" = "200" ]; then
    ok "HTTP 200 on port $PORT  (http://$(ipconfig getifaddr en0 2>/dev/null || echo localhost):$PORT)"
else
    bad "dashboard HTTP returned '${CODE:-no response}' on port $PORT"
fi

# ------------------------------------------------------- export + nightly review
say ""
say "=== EXPORT / REVIEW ==="
if AGE=$(age_of logs/export.log); then
    if [ "$AGE" -gt "$EXPORT_MAX_AGE" ]; then
        warn "export.log stale — $(pretty_age "$AGE")"
    else
        ok "export ran $(pretty_age "$AGE")"
    fi
else
    warn "logs/export.log missing"
fi

INBOX_N=$(ls reports/inbox/*.md 2>/dev/null | wc -l | xargs)
if [ "${INBOX_N:-0}" -gt 0 ]; then
    ok "$INBOX_N archived Telegram message(s) — newest: $(basename "$(ls -t reports/inbox/*.md | head -1)")"
else
    say "  · inbox empty (forward a Telegram msg to the bot to archive it)"
fi

LATEST_REVIEW=$(ls -t reports/review-*.md 2>/dev/null | head -1)
if [ -n "$LATEST_REVIEW" ]; then
    if [ "$(basename "$LATEST_REVIEW")" = "review-$(date +%F).md" ]; then
        ok "review report for today present ($LATEST_REVIEW)"
    else
        warn "newest review is $(basename "$LATEST_REVIEW") — none yet today (job fires 20:00)"
    fi
else
    warn "no reports/review-*.md yet — nightly review has never produced output"
fi

# ------------------------------------------------------------------ sleep guard
say ""
say "=== SLEEP GUARD ==="
# StartInterval agents do not fire during dark wake. If any power source has a
# nonzero idle-sleep timer and disablesleep is off, expect silent trading gaps.
BAD_SLEEP=$(pmset -g custom 2>/dev/null | awk '$1=="sleep" && $2!=0 {print $2; exit}')
DISABLED=$(pmset -g custom 2>/dev/null | awk '$1=="disablesleep" {print $2; exit}')
if [ -n "$BAD_SLEEP" ] && [ "${DISABLED:-0}" != "1" ]; then
    warn "idle sleep is ${BAD_SLEEP} min and disablesleep is off — cycles will stall when it sleeps"
    say "      fix: sudo pmset -a sleep 0 disablesleep 1"
    ASSERT=$(pmset -g 2>/dev/null | grep -o "sleep prevented by.*")
    [ -n "$ASSERT" ] && say "      (currently only held awake by: ${ASSERT#sleep prevented by }— transient)"
else
    ok "sleep disabled — timers will keep firing"
fi

# ----------------------------------------------------------------------- book
say ""
say "=== BOOK ==="
if [ -f "$DB" ]; then
    say "$(sqlite3 -column -header "$DB" "
        SELECT COUNT(*)                                            AS total,
               SUM(status='OPEN')                                  AS open,
               ROUND(SUM(CASE WHEN status='OPEN' THEN stake_usd ELSE 0 END),2) AS exposure,
               SUM(status IN ('WON','LOST','VOID'))                AS settled,
               SUM(status='WON')                                   AS won,
               SUM(status='LOST')                                  AS lost,
               ROUND(SUM(CASE WHEN status IN ('WON','LOST','VOID') THEN pnl ELSE 0 END),2) AS realized
        FROM bets;" 2>/dev/null)"

    # Past their listed end date but still open. Usually fine — Polymarket often
    # closes a market well after end_date_iso, and the engine correctly waits for
    # actual resolution. Only a long backlog suggests settlement is broken.
    OVERDUE=$(sqlite3 "$DB" "SELECT COUNT(*) FROM bets WHERE status='OPEN' AND resolves_at < strftime('%Y-%m-%dT%H:%M:%S','now');" 2>/dev/null)
    VERY=$(sqlite3 "$DB" "SELECT COUNT(*) FROM bets WHERE status='OPEN' AND resolves_at < datetime('now','-3 days');" 2>/dev/null)
    # Polymarket routinely leaves markets open long past end_date_iso, so a stale
    # OPEN bet is normal, not a failure — warn so it's visible without crying wolf.
    if [ "${VERY:-0}" -gt 0 ]; then
        warn "$VERY bet(s) >3 days past resolve time, still awaiting Polymarket (check UNREAL on the portal)"
    elif [ "${OVERDUE:-0}" -gt 0 ]; then
        ok "$OVERDUE bet(s) past end date awaiting Polymarket resolution (normal)"
    else
        ok "no bets awaiting settlement"
    fi

    say ""
    say "  open positions (by resolve date):"
    say "$(sqlite3 -noheader -list -separator '|' "$DB" "
        SELECT ROUND(entry_price,3), ROUND(stake_usd,2), outcome,
               SUBSTR(COALESCE(question,slug),1,46), SUBSTR(resolves_at,1,10)
        FROM bets WHERE status='OPEN' ORDER BY resolves_at;" 2>/dev/null \
      | awk -F'|' '{printf "   %-6s $%-5s %-10s %-46s %s\n", $1, $2, substr($3,1,10), $4, $5}')"
else
    bad "$DB not found"
fi

# --------------------------------------------------------------------- verdict
say ""
say "========================================"
if [ "$FAILS" -gt 0 ]; then
    printf '\033[31mUNHEALTHY\033[0m — %d failure(s), %d warning(s)\n' "$FAILS" "$WARNS"
    exit 1
fi
if [ "$WARNS" -gt 0 ]; then
    printf '\033[33mOK with %d warning(s)\033[0m\n' "$WARNS"
    exit 0
fi
say "$(printf '\033[32mALL HEALTHY\033[0m')"
exit 0
