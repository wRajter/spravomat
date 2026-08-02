#!/usr/bin/env bash
# scripts/process.sh — run the 3x-daily process job, save its log, alert if it fails.

LOG_DIR="$HOME/spravomat-logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/process-$(date -u +%Y%m%d-%H%M%S).log"

cd "$HOME/spravomat" || exit 1
set -a; source .env; set +a
source "$HOME/spravomat/scripts/notify.sh"

# --rm deletes the container, so its output is saved to $LOG first.
docker compose run --rm batch python -m spravomat.orchestration.process > "$LOG" 2>&1
code=$?

if [ "$code" -ne 0 ]; then
    notify "❌ Spravomat process failed (exit $code)" "$LOG

$(tail -20 "$LOG")"
fi

find "$LOG_DIR" -name '*.log' -mtime +14 -delete
exit $code
