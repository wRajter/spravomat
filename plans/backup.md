# Plan — Daily Postgres backup (pg_dump, local, 7-day retention)

> Un-parks the "DB backups" item from `plans/deploy.md`. On a single VPS the
> `pgdata` named volume is the ONLY copy of the data — a dropped table or a bad
> migration is currently unrecoverable. Scope here: local dumps on the box.
> Off-box copy is explicitly NOT in this task (see Not in this task).

## Decisions

### Where the code lives
```
scripts/backup_db.sh      # new dir — host-level ops script
plans/backup.md           # this file
```

Shell, not Python. Backups are infrastructure, not pipeline. A `.sh` script runs
from host cron with zero dependencies — it still works if the venv, the batch
image, or the app itself is broken, which is exactly when you need a backup.
Putting it in `spravomat/` would also fight the `CLAUDE.md` rule that DB access
goes through `db` repository functions; `pg_dump` is not that, it is an ops tool
operating on the whole database.

### Where the dumps live
`/home/lubomir/backups/postgres/`, overridable via the `BACKUP_DIR` env var.

NOT inside the repo. The repo is git-managed by a read-only deploy key and
`git pull` is the deploy step — binary dumps in the working tree are asking to be
committed, clobbered by a checkout, or dragged into the Docker build context.

### How pg_dump is invoked
`docker compose exec -T db pg_dump ...`, redirected to a file on the host.

- `exec` on the already-running `db` container, not `run --rm`: no extra
  container, and `pg_dump` is guaranteed to be the same major version as the
  server (both are `postgres:17`). `db` has `restart: unless-stopped`, so it is up.
- `-T` disables the TTY, so the binary stream is not mangled under cron.
- The dump is written on the HOST via shell redirection — no volume mount needed.

### Dump format — `-Fc` (custom)
Compressed by default and restorable selectively with `pg_restore` (single table,
schema-only, etc.). Plain SQL + gzip would also work but loses selective restore.
Filename: `spravomat-YYYYMMDD-HHMMSS.dump` (UTC stamp, sorts chronologically).

### Credentials — none passed
Inside the container `pg_dump` connects over the local Unix socket, which the
official Postgres image trusts. So `-U "$POSTGRES_USER" -d "$POSTGRES_DB"` is
enough and no password appears in the host process list or in the log.
`POSTGRES_USER` / `POSTGRES_DB` come from sourcing the repo's `.env`.

### Failure handling
- `set -euo pipefail` — any failing step aborts with a non-zero exit, which cron
  surfaces (mail + the log file).
- Write to `TARGET.tmp`, rename to `TARGET` only after success. A crashed or
  truncated dump therefore never looks like a valid backup, and retention never
  counts one.
- Cheap integrity proof: `pg_restore --list` the fresh dump. An unreadable file
  fails here, at 03:10 on a normal day, instead of during a real emergency restore.

### Retention — 7 days
`find "$BACKUP_DIR" -maxdepth 1 -name 'spravomat-*.dump' -type f -mtime +7 -delete`

Note the off-by-one, it is deliberate: `-mtime +7` deletes files STRICTLY older
than 7 days, so at steady state you hold 7 full days plus today = 8 files. If
exactly 7 files is ever wanted, switch to keep-N-newest instead.

Disk cost is negligible: retention already caps `articles` at 3 days, so a
compressed dump is single-digit MB. 8 of them against a 40 GB disk is nothing.

### Roles are not dumped
`pg_dump` is database-scoped and does not include roles. That is fine here: the
single role is recreated from `POSTGRES_USER` / `POSTGRES_PASSWORD` when the
volume is initialised. No `pg_dumpall -g` needed.

## Cron

```cron
10 3 * * * /home/lubomir/spravomat/scripts/backup_db.sh >> /home/lubomir/backups/backup.log 2>&1
```

**03:10 UTC.** Chosen against the existing jobs (verified with `crontab -l` on the
server, 2026-07-30):

```cron
# collect: hourly at :30
30 * * * *      flock -n /tmp/spravomat.lock -c 'cd ~/spravomat && docker compose run --rm batch python -m spravomat.orchestration.collect'
# process: 05:00, 11:00, 19:00 UTC
0 5,11,19 * * * flock -n /tmp/spravomat.lock -c 'cd ~/spravomat && docker compose run --rm batch python -m spravomat.orchestration.process'
```

No `process` run is near 03:10, and the 03:30 `collect` is 20 minutes later — a
few-MB dump is long finished by then.

### The backup does NOT take the shared lock
`collect` and `process` share `/tmp/spravomat.lock` with `flock -n` so they can
never run concurrently (protects the 4 GB RAM budget against two batch runs).
The backup deliberately stays out of that: with `-n` it would silently SKIP
itself whenever a batch happened to be running, and skipped backups are worse
than none — you would believe you had one. `pg_dump` is light and read-only, so a
quiet slot is sufficient protection.

## Restore (write this into the script header too)

Full restore into a running `db` container:
```bash
cat spravomat-YYYYMMDD-HHMMSS.dump | \
  docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists
```
Inspect a dump without restoring:
```bash
docker compose exec -T db pg_restore --list < spravomat-YYYYMMDD-HHMMSS.dump
```
`--clean --if-exists` drops the existing objects first, so the restore is not
appended on top of current data.

## Build order
1. `scripts/backup_db.sh` + `chmod +x`.
2. Test on the server by hand — confirm a `.dump` appears with a sane size, and
   that `pg_restore --list` reads it.
3. Install the cron line.
4. Verify the next morning that `backup.log` shows a clean run.

## Also fix while here
- `README.md:255` says `process` runs at 06/12/18 UTC. Reality is 05/11/19.
- `plans/deploy.md:57` — mark the backup half of that to-do as done.
- Add `backups/` to `.gitignore` as cheap insurance, in case a dump is ever
  written inside the repo by accident.

## Not in this task (deliberately deferred)
- **Off-box copy.** Local dumps cover "I dropped a table", NOT "the VPS is gone".
  This is the real remaining gap and should be the next step (e.g. rclone/scp to
  Hetzner Storage Box or B2).
- **Log rotation.** `spravomat-cron.log` and the new `backup.log` grow forever.
  Slow-burn on a 40 GB disk, not urgent.
- **Restore drill.** Actually restoring a dump into a throwaway database to prove
  the whole path works end to end. Worth doing once, separately.
- **Keeping the crontab in git.** The schedule currently lives only in
  `/var/spool/cron/crontabs/lubomir` on the server — not version-controlled, not
  backed up. Could become `scripts/crontab.txt` installed with one command.
