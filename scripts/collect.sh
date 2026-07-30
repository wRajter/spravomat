#!/usr/bin/env bash
# scripts/collect.sh — run the hourly collect job, save its log, alert if it fails.

LOG_DIR="$HOME/spravomat-logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/collect-$(date -u +%Y%m%d-%H%M%S).log"

cd "$HOME/spravomat" || exit 1
set -a; source .env; set +a

# --rm deletes the container, so its output is saved to $LOG first.
docker compose run --rm batch python -m spravomat.orchestration.collect > "$LOG" 2>&1
code=$?

if [ "$code" -ne 0 ]; then
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
        --data-urlencode "text=❌ Spravomat collect failed (exit $code)
$LOG

$(tail -20 "$LOG")" > /dev/null
fi

find "$LOG_DIR" -name '*.log' -mtime +14 -delete
exit $code
