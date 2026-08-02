#!/bin/bash
# run_bot.sh — Auto-restart wrapper for the Polymarket Copy Trading Bot.
# Restarts automatically on crash with a 10-second cooldown.
# Usage: nohup bash run_bot.sh &
#
# Logs rotate daily: /tmp/bot_YYYY-MM-DD.log
# PID file: /tmp/polybot.pid

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="/tmp/polybot.pid"
MAX_RESTARTS=50          # max restarts per day before giving up
COOLDOWN_SECONDS=10      # wait between restarts
restarts_today=0
last_restart_date=""

cleanup() {
    echo "[$(date)] Shutting down bot wrapper..."
    if [ -f "$PID_FILE" ]; then
        BOT_PID=$(cat "$PID_FILE")
        kill "$BOT_PID" 2>/dev/null || true
        rm -f "$PID_FILE"
    fi
    # Kill any leftover processes on port 8050
    lsof -ti:8050 2>/dev/null | xargs kill -9 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "[$(date)] Bot wrapper started in $SCRIPT_DIR"

while true; do
    today=$(date +%Y-%m-%d)
    LOG_FILE="/tmp/bot_${today}.log"

    # Reset daily restart counter
    if [ "$today" != "$last_restart_date" ]; then
        restarts_today=0
        last_restart_date="$today"
    fi

    # Safety: don't restart forever
    if [ "$restarts_today" -ge "$MAX_RESTARTS" ]; then
        echo "[$(date)] Hit max restarts ($MAX_RESTARTS) for today. Stopping." | tee -a "$LOG_FILE"
        break
    fi

    # Kill any stale processes
    lsof -ti:8050 2>/dev/null | xargs kill -9 2>/dev/null || true
    sleep 2

    echo "[$(date)] Starting bot (restart #$restarts_today)..." | tee -a "$LOG_FILE"

    # Start the bot
    python3 main.py >> "$LOG_FILE" 2>&1 &
    BOT_PID=$!
    echo "$BOT_PID" > "$PID_FILE"
    echo "[$(date)] Bot PID: $BOT_PID" | tee -a "$LOG_FILE"

    # Wait for the bot to exit
    wait "$BOT_PID" || true
    EXIT_CODE=$?

    rm -f "$PID_FILE"
    restarts_today=$((restarts_today + 1))

    echo "[$(date)] Bot exited with code $EXIT_CODE. Restarting in ${COOLDOWN_SECONDS}s..." | tee -a "$LOG_FILE"
    sleep "$COOLDOWN_SECONDS"
done
