# scripts/notify.sh — send a Telegram alert. Sourced by the other ops scripts.
#
# Plain shell + curl on purpose: an alert has to work when the app image, the
# venv, or the database is the thing that is broken. See plans/logging.md.
#
# Use as a library (the normal case):
#     source "$(dirname "${BASH_SOURCE[0]}")/notify.sh"
#     notify "❌ Spravomat: process FAILED" "$(tail -n 30 "$LOG_FILE")"
#
# Or run it directly to test:
#     ./scripts/notify.sh "test subject" "test body"
#
# Deliberately NO `set -euo pipefail` here: this file is sourced, and changing
# the caller's shell options from a library is a nasty surprise.

# Telegram rejects messages over 4096 characters. Stay under it with room for
# the subject and the truncation notice.
NOTIFY_MAX_CHARS=3800

notify() {
    local subject="$1"
    local body="${2:-}"

    # Load credentials only if the caller has not already sourced .env.
    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
        local repo_dir
        repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
        if [ -f "$repo_dir/.env" ]; then
            set -a
            # shellcheck disable=SC1091
            source "$repo_dir/.env"
            set +a
        fi
    fi

    # Alerting not configured is a warning, never an error: a missing token must
    # not turn a successful backup into a failed one.
    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
        echo "⚠️ Telegram not configured (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID unset) — alert not sent"
        echo "⚠️ Would have sent: $subject"
        return 0
    fi

    local text="$subject"
    if [ -n "$body" ]; then
        text="$subject"$'\n\n'"$body"
    fi

    if [ "${#text}" -gt "$NOTIFY_MAX_CHARS" ]; then
        text="${text:0:$NOTIFY_MAX_CHARS}"$'\n\n[truncated — see the full log on the server]'
    fi

    # No parse_mode: log lines contain _ * [ ] ` which Telegram's Markdown parser
    # rejects, and a rejected alert is worse than an unformatted one.
    local http_code
    http_code="$(curl -sS --max-time 15 -o /dev/null -w '%{http_code}' \
        -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
        --data-urlencode "text=${text}" \
        --data-urlencode "disable_web_page_preview=true" 2>&1)" || http_code="000"

    if [ "$http_code" = "200" ]; then
        echo "ℹ️ Telegram alert sent"
    else
        # Never leak the token into a log file.
        echo "❌ Telegram alert FAILED (HTTP $http_code) — subject was: $subject"
    fi

    return 0
}

# Executed directly rather than sourced → act as a small CLI for testing.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    if [ $# -lt 1 ]; then
        echo "Usage: $0 \"subject\" [\"body\"]" >&2
        exit 2
    fi
    notify "$@"
fi
