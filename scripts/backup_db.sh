#!/usr/bin/env bash
# scripts/backup_db.sh — daily pg_dump of the Postgres `db` container.
#
# Plain shell on purpose: backups are infrastructure, not pipeline. No venv, no
# app image, no Python — so this still works when the app itself is broken,
# which is exactly when a backup matters. Full rationale: plans/backup.md
#
# Run by host cron (03:10 UTC — clear of the collect/process jobs):
#   10 3 * * * /home/lubomir/spravomat/scripts/backup_db.sh >> /home/lubomir/backups/backup.log 2>&1
#
# Restore a dump into the running db container:
#   cat spravomat-YYYYMMDD-HHMMSS.dump | docker compose exec -T db \
#     pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists
# Inspect a dump without restoring it:
#   docker compose exec -T db pg_restore --list < spravomat-YYYYMMDD-HHMMSS.dump

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# compose needs the repo dir: that is where docker-compose.yml and .env live.
cd "$REPO_DIR"

# POSTGRES_USER / POSTGRES_DB. No password needed: inside the container pg_dump
# uses the local Unix socket, which the official postgres image trusts. Nothing
# sensitive reaches the host process list or this log.
set -a
source .env
set +a

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
TARGET="$BACKUP_DIR/spravomat-$STAMP.dump"

# Never leave a half-written dump behind for retention to count as a backup.
trap 'rm -f "$TARGET.tmp"' ERR INT TERM

echo "🚀 Backup starting → $TARGET"

# -Fc = custom format: compressed, and pg_restore can restore selectively.
# -T  = no TTY, otherwise the binary stream gets mangled under cron.
# exec (not run --rm) reuses the live container, so pg_dump always matches the
# server's major version. The file is written here on the host by redirection.
docker compose exec -T db \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$TARGET.tmp"

# Cheap integrity proof: an unreadable dump fails now, on a quiet morning,
# instead of during a real restore.
docker compose exec -T db pg_restore --list < "$TARGET.tmp" > /dev/null

# Only a verified dump earns the real filename.
mv "$TARGET.tmp" "$TARGET"
echo "ℹ️ Backup OK ($(du -h "$TARGET" | cut -f1))"

# -mtime +N deletes files STRICTLY older than N days, so 7 keeps 7 full days
# plus today = 8 files at steady state. Deliberate; see plans/backup.md.
PRUNED="$(find "$BACKUP_DIR" -maxdepth 1 -name 'spravomat-*.dump' -type f \
    -mtime "+$RETENTION_DAYS" -print -delete | wc -l | tr -d ' ')"
echo "ℹ️ Retention: pruned $PRUNED dump(s) older than $RETENTION_DAYS days"

echo "🏁 Backup finished"
