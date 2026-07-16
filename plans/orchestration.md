# Plan — orchestration

## Purpose
Run the pipeline steps in order, automatically, on a schedule. Orchestration
adds NO new functionality — it wires the existing components (acquisition,
grouping, presentation) into scheduled, fail-fast runs, plus a retention step.

## Principle — stays thin
Orchestration knows only HOW TO RUN steps and in WHAT ORDER. It does not know
what's inside them (calls acquisition.run(), grouping.run(), etc. as black
boxes). The order lives in one place (the orchestration script); the scheduler
is just a dumb trigger.

## Two separate runs (different frequencies)
Split because data collection must be frequent (RSS feeds roll fast — miss a
window and articles are lost forever), while processing doesn't need to be.

### Run 1 — collection (frequent, e.g. hourly)
acquisition.run()  ->  retention (delete articles older than 3 days)

- Keeps data fresh and bounded. "Add new, drop old" = data maintenance.
- fail-fast: if acquisition fails, retention still runs? -> NO, keep it simple:
  sequential fail-fast (if a step fails, stop and log). Confirm in module design.

### Run 2 — processing (3x/day: 06:00, 12:00, 18:00; night off)
grouping.run()  ->  presentation.run()

- Rebuilds clusters and story cards. Grouping always receives already-bounded
  data (max 3 days), since retention ran in Run 1.

## Retention
- New step: delete articles older than 3 days (by published_at or fetched_at —
  confirm which in design).
- Lives with collection (Run 1). ON DELETE CASCADE already cleans article_clusters.
- A db repository function (delete_articles_older_than) — orchestration calls it,
  never touches SQL.
- 3-day window also keeps clustering volume small/constant — bounds the N we
  worried about.

## Scheduling — Heroku Scheduler
- Scheduler triggers one command per run (dumb trigger).
- The order + fail-fast logic lives in the orchestration script(s), NOT in
  scheduler config.
- Two scheduled commands: one for Run 1 (frequent), one for Run 2 (3x/day).
- Heroku Scheduler has coarse resolution (10 min / hourly / daily) — confirm it
  can express "3x a day at fixed times", or whether the script self-checks the
  hour. (Open question below.)

## Alerting — PARKED for v1
- v1: logs only (Heroku captures stdout/stderr). If a step fails, it's logged.
- Push alerting (email etc.) is a later task — no Slack, form undecided.

## Overlap guard — flag for design
- If a run is still going when the next fires, two processes could clash.
- Confirm whether this needs an explicit guard for v1, or if run durations make
  it unlikely (collection is fast; processing 3x/day is unlikely to overlap).

## Dependency on db
- New repository function: delete_articles_older_than(days) — used by retention.

## Parked / open questions
- Alerting form (email / other) — parked.
- Heroku Scheduler resolution for "3x/day at fixed times" vs script self-check.
- Overlap guard — needed for v1?
- Retention basis: published_at vs fetched_at.

---

# Claude's review (2026-07-16)

Overall: good and correctly scoped — orchestration stays thin (order + trigger
only, components as black boxes), two-runs-by-frequency is the right split,
retention lives with collection, alerting parked. Consistent with what we built
(each component exposes a clean `run() -> {success, ...}`). Answer inline
(`A:` lines). No code until resolved.

Note: the POC `cron_jobs.txt` (local crontab + online clustering + CSV) does NOT
port — reference only. We build fresh on Heroku Scheduler, batch-only, DB.

## Questions I need you to answer

### Q1 — retention basis
Recommend `fetched_at`, NOT `published_at`. `published_at` is NULLABLE (some
feeds omit it) — retention on a nullable column is unreliable (null rows never
age out / need special-casing). `fetched_at` is NOT NULL (DB default now()),
monotonic with ingestion, guarantees every article ages out. Downside (article
published 5 days ago but first seen today lives 3 more days) is harmless —
display freshness is handled by ranking/grouping scores.
A: Use fetched_at, not published_at. You're right — published_at is nullable, so
retention on it is unreliable (null rows never age out). fetched_at is NOT NULL
and monotonic, so every article ages out cleanly. The "published 5 days ago,
seen today, lives 3 more" case is harmless — display freshness is handled by
ranking/scoring, not retention.

### Q2 — retention window (days)
Confirm 3 days (POC used 7). Implies ~3 x ~600/day ≈ ~1,800 articles as
grouping's steady-state input. That's fine (similarity matrix ~1800² ≈ 26 MB,
embedding ~1–2 min). Confirm the number and that we're comfortable with that N.
A: Confirmed, 3 days (~1800 articles). The N is comfortable (~26 MB matrix,
1–2 min embedding) — well clear of the scaling ceilings. The 3-day window keeps
grouping's input small and constant.

### Q3 — fail-fast in Run 1
Run 1 = acquisition -> retention, sequential fail-fast (if acquisition returns
success=False, skip retention). This is fine: acquisition.run() is internally
resilient (per-feed failures don't abort it; it returns False only on a
catastrophic top-level error), so a False is genuinely exceptional and skipping
retention for one cycle is harmless (runs next hour). Confirm.
A: Confirmed. Run 1 = acquisition -> retention, sequential fail-fast. acquisition
is internally resilient, so a top-level False is genuinely exceptional; skipping
retention for one cycle is harmless (runs next hour).

### Q4 — overlap guard
Recommend NONE for v1. Durations are short (steady-state collection is seconds
now that dedup runs first; processing ~35s). Even if two runs overlap,
ON CONFLICT (url) DO NOTHING makes double-insert safe, and Postgres MVCC gives
grouping a consistent snapshot while retention deletes. Worst case is a little
wasted perex scraping, never corruption. Confirm no guard for v1.
A: Confirmed — NO overlap guard for v1. Runs are short, overlap unlikely, and
even if it happens: ON CONFLICT (url) DO NOTHING makes inserts safe and MVCC
gives grouping a consistent snapshot. Worst case is wasted perex scraping, never
corruption. (Revisit only if run durations grow substantially.)

### Q5 — Heroku Scheduler for "3x/day at fixed times"
Heroku Scheduler only does every-10-min / hourly / daily-at-one-time.
  (a) Three daily Scheduler jobs (06:00 / 12:00 / 18:00 UTC), all running the
      SAME Run-2 command. Script stays a dumb one-shot (fires -> runs once) —
      matches "scheduler is a dumb trigger". My recommendation.
  (b) One hourly job whose script self-checks `if hour in {6,12,18}` — puts time
      logic in the script (21 no-op wake-ups/day), violates "dumb trigger".
Caveat either way: Heroku Scheduler runs in UTC, so Bratislava times drift ±1h
with DST — fine for "morning/noon/evening" v1. Pick (a) or (b).
A: (a) — three separate daily Scheduler jobs (06:00 / 12:00 / 18:00 UTC), all
running the same Run-2 command. Keeps the script a dumb one-shot; scheduler stays
a dumb trigger. UTC vs Bratislava ±1h DST drift is irrelevant for
morning/noon/evening v1.

### Q6 — entry-point shape
Two runnable commands, mirroring the `__main__` pattern of the other components:
  - `python -m spravomat.orchestration.collect`  -> acquisition.run() -> retention
  - `python -m spravomat.orchestration.process`  -> grouping.run() -> presentation.run()
Each sets up logging, calls the component run()s in order, fail-fast on
success=False, exits non-zero on failure (so Heroku logs it). Plus one new db
function `delete_articles_older_than(days)`. Confirm this shape.
A: Confirmed. Two commands: `python -m spravomat.orchestration.collect`
(acquisition -> retention) and `python -m spravomat.orchestration.process`
(grouping -> presentation). Each sets up logging, calls run()s in order,
fail-fast on success=False, exits non-zero on failure. Plus the new db function
delete_articles_older_than(days).