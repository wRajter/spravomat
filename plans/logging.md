# Plan — Logging + failure alerts (Telegram)

> Goal: when a batch run fails, get a Telegram alert, SSH in, and find the exact
> failing step in seconds. Today a failure is silent and the logs make "where did
> it break" hard to answer.
>
> Status: PROPOSAL. Nothing implemented yet.

## 1. How logging actually works today (verified in the repo)

**It does NOT write to a txt file.** Worth correcting up front, because it
changes what needs fixing. The actual chain is:

1. Each entry point calls `logging.basicConfig(...)` with no handler, so Python
   defaults to a `StreamHandler` on **stderr**.
2. Every module logs via `logging.getLogger(__name__)` — correct, standard.
3. `PYTHONUNBUFFERED=1` is set in both `Dockerfile.batch` and `Dockerfile.web`,
   so lines are not held in a buffer. Good — already right.
4. The container writes to stderr; cron redirects it with
   `>> /home/lubomir/spravomat-cron.log 2>&1`.

So the txt file is a **cron artifact, not application behaviour**. The app is
already stdout/stderr-based, which is the container-correct design. No migration
away from file logging is needed — that part is already done.

What IS actually wrong:

| Problem | Where | Why it hurts the debug flow |
|---|---|---|
| **No date in timestamps** | `datefmt="%H:%M:%S"` | The log says `15:11:09` with no day. In an append-only file spanning weeks, you cannot tell which run you are looking at. Worst offender for your workflow. |
| **No logger name in the format** | `format="%(asctime)s %(levelname)s %(message)s"` | You see *what* failed, never *where*. `%(name)s` would print `spravomat.acquisition.rss` vs `spravomat.db.repository` — that is the "and where" half of your requirement, and it is one word of config. |
| **`basicConfig` duplicated 6×** | `orchestration/collect.py:44`, `orchestration/process.py:35`, `acquisition/__main__.py:17`, `grouping/__main__.py:16`, `presentation/__main__.py:16`, `db/migrations/__main__.py:17` | Six copies of the same block that must be edited together. `CLAUDE.md` already assigns logging to `shared` — but `shared/logging.py` does not exist. |
| **One flat file, no rotation** | `spravomat-cron.log` | Grows forever. Finding one failed run inside weeks of hourly `collect` output means grepping by hand. |
| **`--rm` discards container logs** | cron lines | Once the container is gone, `docker compose logs` has nothing. The cron redirect is currently the ONLY copy. |
| **Uncaught exceptions bypass logging** | `run_steps` | Components return the standard dict, but an unexpected raise (network, torch, OOM) prints a bare traceback to stderr with no logger name and no level. |
| **Third-party log noise** | — | `urllib3`, `httpx` (google-genai), `sentence_transformers` log at INFO. Real signal gets buried. |
| **Web access logs are off** | `Dockerfile.web` CMD | Gunicorn does not log requests without `--access-logfile -`. Flask's own logger is never configured, so `create_app()` app-level logs use Flask's default. |
| **Failures are silent** | everywhere | The core gap. A failed run looks exactly like a successful one unless you go looking. |

## 2. The log-vanishing problem (`docker compose run --rm`)

You asked specifically how to still get logs from a failed batch run. Options
considered:

| Option | Verdict |
|---|---|
| Drop `--rm`, use `docker compose logs` | **No.** `plans/deploy.md:83` explicitly warns this fills the 40 GB disk with stopped containers. Correct call, don't undo it. |
| Docker logging driver → journald | **No.** Adds a second place to look, and `run` containers still need finding by ID. More machinery, no gain. |
| Keep the single cron redirect | **Insufficient.** Works, but one flat unrotated file. |
| **Per-run log file via `tee` in a wrapper script** | **Yes.** Recommended. |

**The fix: one wrapper script that owns a batch run.** The container's stdout is
captured to a per-run file on the host *before* the container is removed, so
`--rm` no longer loses anything.

```
scripts/run_batch.sh collect
  → /home/lubomir/spravomat-logs/collect-20260730-153000.log
```

`docker compose run` propagates the container's exit code to the shell, so the
wrapper knows exactly whether the run failed — that is what drives the alert.

This also fixes a problem from the backup work: the schedule currently lives only
in `/var/spool/cron/crontabs/lubomir`, untracked and unbacked-up. With a wrapper,
the cron lines shrink to `scripts/run_batch.sh collect` and all the logic
(`flock`, logging, alerting) moves into git.

### The `flock` exit-code trap — important

Your cron uses `flock -n`. **When the lock is already held, `flock` exits `1`** —
identical to a genuine job failure. Naive exit-code alerting would Telegram you
every time `collect` correctly skipped because `process` was running. False
alarms train you to ignore alerts.

Fix: `flock -n -E 75` makes the lock-unavailable case exit `75` instead. The
wrapper then treats `75` as "skipped, logged, no alert" and anything else
non-zero as a real failure.

## 3. Proposed changes

### 3.1 `spravomat/shared/logging.py` (new)

Closes the gap where `CLAUDE.md` lists logging under `shared` but no file exists.

```python
def setup_logging(level: str | None = None) -> None:
    """Configure root logging for stdout. Idempotent; safe to call twice."""
```

- Single `StreamHandler` on **stdout** (not stderr). App logs are normal output,
  not errors; stderr stays for crashes.
- Format: `%(asctime)s %(levelname)-8s %(name)s | %(message)s`
- `datefmt="%Y-%m-%d %H:%M:%S"` — the date, finally.
- Level from `config.LOG_LEVEL`, overridable by the `level` argument.
- Quiet the noise: `urllib3`, `httpx`, `sentence_transformers`, `feedparser` →
  `WARNING`.
- Idempotent (clear existing root handlers first), so double calls don't
  double-print.

Then replace all **6** `basicConfig` blocks with `setup_logging()`.

### 3.2 `run_steps` — catch and log crashes

Wrap each step in try/except. An unexpected raise becomes
`logger.exception("❌ ...")` — full traceback, through the logger, with the step
label attached — and returns the standard failure dict instead of a bare crash.
Matches the project rule that risky operations return the error dict.

Also log per-step duration (`ℹ️ grouping finished in 41.2s`). Cheap, and it tells
you whether a failure was a timeout or instant.

### 3.3 `scripts/notify.sh` (new) — the Telegram sender

A small sourced helper, `notify "subject" "body"`, used by every ops script.

- Plain `curl` to the Telegram Bot API. **Deliberately shell, not Python** — the
  alert must work when the app image, venv, or DB is the thing that's broken.
- Reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from the repo `.env`.
- **Never fails the caller**: no token configured, or Telegram unreachable →
  log a warning and return 0. An alerting outage must not turn a successful
  backup into a failed one.
- Truncate to Telegram's 4096-char limit.

Setup (one-time, manual): message `@BotFather` → `/newbot` → token. Then message
your new bot once and read `chat_id` from
`https://api.telegram.org/bot<TOKEN>/getUpdates`.

### 3.4 `scripts/run_batch.sh <collect|process>` (new)

The wrapper. One place that owns scheduled batch runs.

```
1. Validate the argument is collect|process.
2. flock -n -E 75 on /tmp/spravomat.lock  → 75 means skip, log, exit 0 quietly.
3. Run `docker compose run --rm batch python -m spravomat.orchestration.<job>`,
   piping through `tee` to a per-run log file.
4. Capture the container's exit code (via PIPESTATUS — tee would otherwise mask it).
5. Exit 0  → log one success line, done. Silence is good news.
   Exit !=0 → notify: job name, exit code, host, log path, last ~30 log lines.
6. Prune log files older than 14 days.
```

Alert message shape — enough to triage from the phone, not a log dump:

```
❌ Spravomat: process FAILED
Exit code: 1
Time: 2026-07-30 19:04:11 UTC
Log: ~/spravomat-logs/process-20260730-190000.log

--- last lines ---
2026-07-30 19:04:10 ERROR    spravomat.presentation.enrichment | ❌ Gemini call failed: 429
2026-07-30 19:04:11 ERROR    spravomat.orchestration | ❌ process failed at presentation: ...
```

With `%(name)s` in the format, the alert itself usually tells you the component —
you SSH in for the traceback, not to find out where to look.

### 3.5 Alert on backup failures too

`scripts/backup_db.sh` currently fails into a log nobody reads. Source
`notify.sh` and alert on failure. Same reasoning, ~3 lines.

### 3.6 Web logging

- `Dockerfile.web` CMD: add `--access-logfile - --error-logfile -` so gunicorn
  requests and errors reach `docker compose logs web`.
- `create_app()`: call `setup_logging()` so app-level logs use the same format.
- The `web` service is long-running under `restart: unless-stopped`, so
  `docker compose logs web` already works. Add `logging` limits in
  `docker-compose.yml` (`max-size: 10m`, `max-file: 3`) so the json-file driver
  cannot fill the disk. **This is worth doing regardless of the rest of the plan.**

### 3.7 New env vars (`.env.example`)

```
# --- Alerting (Telegram) ---
# Empty = alerting disabled (scripts log a warning and carry on).
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## 4. How to reach the logs after an alert

Deliberately boring — three commands:

```bash
ls -lt ~/spravomat-logs/ | head          # newest runs first
less ~/spravomat-logs/process-20260730-190000.log   # the run named in the alert
grep -h ERROR ~/spravomat-logs/*.log | tail -20     # recent errors across runs
docker compose logs -f web               # live web logs (unaffected by --rm)
```

Optional convenience wrapper, `scripts/logs.sh [collect|process]`, that tails the
newest matching log. Nice-to-have, not core.

## 5. New cron layout

```cron
# collect: hourly at :30
30 * * * *      /home/lubomir/spravomat/scripts/run_batch.sh collect
# process: 05:00, 11:00, 19:00 UTC
0 5,11,19 * * * /home/lubomir/spravomat/scripts/run_batch.sh process
# backup: daily 03:10 UTC
10 3 * * *      /home/lubomir/spravomat/scripts/backup_db.sh
```

No `flock`, no `cd`, no redirect in the crontab — the scripts own all of it. Short
enough to read, and the logic is version-controlled.

## 6. Build order (each step independently testable)

1. `shared/logging.py` + replace the 6 `basicConfig` blocks. Test locally: run
   `collect` and confirm the new format with date + logger name.
2. `run_steps` try/except + step durations. Test by making a step raise.
3. `notify.sh` + the two env vars. Test: `notify "test" "hello"` → phone.
4. Wire `notify.sh` into `backup_db.sh` (smallest real integration).
5. `run_batch.sh`. Test all three paths on the VPS: success, forced failure
   (bad command), and lock-held skip (start `process`, then run `collect`).
6. Swap the cron lines over.
7. `Dockerfile.web` gunicorn flags + compose `logging` limits.

Steps 1–2 are app code; 3–6 are ops. They can land as two separate commits.

## 7. Open questions for Lubomir

- **Alert storms.** `collect` runs hourly. If the DB dies at 02:00, you get ~24
  identical alerts overnight. Options: (a) alert every time — noisy but never
  misses; (b) suppress repeats via a flag file, e.g. at most one alert per job per
  6 hours; (c) alert on the 1st, 2nd, then every 6th failure. My recommendation:
  start with (a) for a week to see the real failure rate, then add (b) if it's
  annoying. Cheap either way.
- **Should a successful run ever notify?** Recommend no — silence means healthy.
  But then "cron never fired at all" is invisible (see Deferred: heartbeat).
- **Log retention: 14 days?** Hourly `collect` at a few KB per run is roughly
  350 files / ~10 MB per fortnight. Negligible; could easily be 30 days.
- **Do you want web 500s alerting too?** Different mechanism (log scanning or a
  Flask `errorhandler`), and a crawler hitting a bad URL would page you. Suggest
  deferring until batch alerting has proven itself.

## 8. Deferred (deliberately not in this plan)

- **Heartbeat / dead-man's switch.** Alerting on failure cannot detect cron
  itself being dead, or the VPS being off. The real fix is an external pinger
  (healthchecks.io free tier: one `curl` at the end of a successful run; it pages
  you when the ping *stops*). This is the only gap that alerting-on-failure
  structurally cannot close — worth doing soon, but it's a separate change.
- **`pipeline_runs` table.** Persisting run history (job, started, duration,
  status, counts) in Postgres would give trends and a web status page.
  `CLAUDE.md` allows this as observability — outside the pipeline, and the
  pipeline must never read it. Deferred: files answer "why did last night fail?"
  today; a table is for "how often does this fail?", a question you don't have yet.
- **Centralised log shipping** (Loki/Grafana, hosted log service). Overkill for
  one box; `ssh` + `less` is genuinely fine at this scale.
- **`logrotate` for `spravomat-cron.log`.** Becomes obsolete once cron stops
  redirecting into it. Delete the old file after step 6 instead.
- **Structured JSON logs.** Only useful with a log aggregator. Human-readable
  wins while `less` is the reader.
