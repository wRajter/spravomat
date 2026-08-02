#!/usr/bin/env bash
# scripts/collect.sh — run the hourly collect job, save its log, alert if it fails.

LOG_DIR="$HOME/spravomat-logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/collect-$(date -u +%Y%m%d-%H%M%S).log"

cd "$HOME/spravomat" || exit 1
set -a; source .env; set +a
source "$HOME/spravomat/scripts/notify.sh"

# --rm deletes the container, so its output is saved to $LOG first.
docker compose run --rm batch python -m spravomat.orchestration.collect > "$LOG" 2>&1
code=$?

if [ "$code" -ne 0 ]; then
    notify "❌ Spravomat collect failed (exit $code)" "$LOG

$(tail -20 "$LOG")"
fi

find "$LOG_DIR" -name '*.log' -mtime +14 -delete
exit $code
