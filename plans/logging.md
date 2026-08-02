# Logging + failure alerts (Telegram)

> Goal: when a batch run fails, get a Telegram alert, SSH in, and find the exact
> failing step in seconds.
>
> Status: IMPLEMENTED. This describes what is built. See commits `1e4c7c3`
> (logging), `adf452f` + `ac901d5` (scripts + alerts).

## How it works

Three layers, bottom to top:

1. **`spravomat/shared/logging.py`** — the one place that configures logging.
   `setup_logging()` sends everything to **stdout** with the format
   `%(asctime)s %(levelname)-8s %(name)s | %(message)s` (full date, and the
   logger name so you see *where* a line came from). It is idempotent (clears
   existing root handlers first) and quiets noisy libraries (`urllib3`, `httpx`,
   `httpcore`, `sentence_transformers`, `transformers`, `filelock`) to WARNING.
   Only entry points call it; library modules just use
   `logging.getLogger(__name__)`.

2. **`orchestration/run_steps`** — runs pipeline steps in order, fail-fast, and
   logs a consistent story: `🚀 started` → per-step `✅ label (2.3s): msg` →
   `🏁 completed`. Each step is timed. A step that raises is caught, logged with
   its traceback via `logger.exception`, and turned into the standard failure
   dict — the caller always gets an exit code, never a bare crash.

3. **`scripts/collect.sh` / `scripts/process.sh`** — the batch container runs
   with `--rm`, so each wrapper redirects its stdout/stderr to a per-run file in
   `~/spravomat-logs/` *before* the container is deleted. On non-zero exit it
   sends a Telegram alert (log path + last 20 lines). Logs older than 14 days
   are pruned.

`scripts/notify.sh` is a sourceable Telegram sender (`notify "subject" "body"`).
Deliberately plain shell + curl so it still works when the app image, venv, or
DB is the thing that broke. It never fails the caller: unconfigured token or
Telegram outage → warn and return 0.

## The log-vanishing problem (`docker compose run --rm`)

`--rm` is kept on purpose (`plans/deploy.md:83` — stopped containers fill the
40 GB disk). The per-run file written by the wrapper is the copy that survives.

## How to reach the logs after an alert

```bash
ls -lt ~/spravomat-logs/ | head          # newest runs first
less ~/spravomat-logs/process-<ts>.log   # the run named in the alert
grep -h ERROR ~/spravomat-logs/*.log | tail -20
docker compose logs -f web               # live web logs (unaffected by --rm)
```

## Known gaps / divergences from the original plan

- **`notify.sh` is not wired into `collect.sh` / `process.sh`.** Those two
  scripts inline their own `curl` instead of sourcing `notify.sh`. Worth
  reconciling so the alert logic lives in one place. `backup_db.sh` is the
  intended consumer of `notify.sh`.
- **No `flock` / single `run_batch.sh` wrapper.** The plan proposed one wrapper
  with `flock -n -E 75` lock-skip handling; the build went with two separate
  scripts and no locking. Fine as long as collect and process runs don't
  overlap in practice.

## Deferred (not built)

- **Heartbeat / dead-man's switch** (e.g. healthchecks.io). Alerting-on-failure
  cannot detect cron itself being dead or the VPS being off. The one gap this
  design structurally can't close — worth doing soon.
- **`pipeline_runs` table** — persist run history for trends / a status page.
  Allowed as observability, but answers "how often does this fail?", a question
  we don't have yet. Files answer "why did last night fail?" today.
- **Web request logging** — gunicorn `--access-logfile -` and compose
  `logging` size limits.
- **Alert-storm suppression** — hourly `collect` could send ~24 identical
  alerts overnight if the DB dies. Start noisy, add a flag-file cooldown if it
  gets annoying.
- **Centralised log shipping / JSON logs** — overkill for one box; `ssh` +
  `less` is fine at this scale.
