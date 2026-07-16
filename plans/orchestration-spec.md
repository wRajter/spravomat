# Spec — orchestration (finalized)

> Authoritative spec to build against. Consolidates the decisions made in
> `orchestration.md` (kept as reference + full Q&A rationale). Finalized
> 2026-07-16.

## Purpose
Run the pipeline steps in order, automatically, on a schedule. Orchestration
adds NO new functionality — it wires the existing components into scheduled,
fail-fast runs, plus a retention step.

## Principle — stays thin
Orchestration knows only HOW TO RUN steps and in WHAT ORDER. It calls
`acquisition.run()`, `grouping.run()`, `presentation.run()` as black boxes —
never touches their internals or SQL. The order lives in the orchestration
scripts; the scheduler is a dumb trigger.

## Two runs (split by frequency)
Collection must be frequent (RSS feeds roll fast — miss a window and articles
are lost); processing does not.

### Run 1 — collection (frequent, hourly)
```
acquisition.run()  ->  retention (delete articles older than 3 days)
```
Sequential fail-fast: if `acquisition.run()` returns `success=False`, stop and
log — skip retention. This is safe: acquisition is internally resilient (per-feed
failures don't abort it; it returns False only on a catastrophic top-level
error), so a False is genuinely exceptional and skipping retention for one cycle
is harmless (it runs next hour).

### Run 2 — processing (3x/day: 06:00 / 12:00 / 18:00 UTC; night off)
```
grouping.run()  ->  presentation.run()
```
Sequential fail-fast: if grouping fails, don't run presentation. Grouping always
receives already-bounded data (<= 3 days), since retention runs in Run 1.

## Retention
- Delete articles older than **3 days by `fetched_at`** (NOT `published_at`).
  `fetched_at` is NOT NULL (DB default now()) and monotonic, so every article
  ages out cleanly; `published_at` is nullable and unreliable for retention.
  Display freshness is handled by ranking/grouping scores, not retention.
- `ON DELETE CASCADE` on `article_clusters` cleans cluster rows automatically.
  (Story cards are full-replaced by presentation each run, so no orphan cleanup
  needed there.)
- 3-day window bounds grouping's input to ~1,800 articles steady-state — small,
  constant N (similarity matrix ~26 MB, embedding ~1–2 min). Comfortable.
- Implemented via a new db repository function `delete_articles_older_than(days)`
  — orchestration calls it, never touches SQL.

## Overlap guard — NONE for v1
Runs are short (steady-state collection is seconds now that dedup runs first;
processing ~35s), so overlap is unlikely. Even if two runs overlap:
`ON CONFLICT (url) DO NOTHING` makes inserts safe, and Postgres MVCC gives
grouping a consistent snapshot while retention deletes. Worst case is a little
wasted perex scraping, never corruption. Revisit only if durations grow.

## Scheduling — Heroku Scheduler
- **Run 1**: one hourly Scheduler job → the collect command.
- **Run 2**: THREE daily Scheduler jobs (06:00 / 12:00 / 18:00 UTC), each running
  the SAME process command. This keeps each script a dumb one-shot (fires → runs
  once); no time logic in the script.
- Heroku Scheduler runs in UTC; Bratislava drift is ±1h with DST — irrelevant for
  a morning/noon/evening cadence in v1.
- The commands are configured in the Heroku Scheduler add-on dashboard, NOT the
  Procfile. Procfile stays `web` + `release` (migrations). Scheduler runs each
  command as a one-off dyno.

## Alerting — PARKED for v1
Logs only (Heroku captures stdout/stderr). A failed step is logged and exits
non-zero. Push alerting (email/other) is a later task; form undecided.

## Entry-point shape
Two runnable commands, mirroring the `__main__` pattern of the other components:
- `python -m spravomat.orchestration.collect`  → acquisition.run() → retention
- `python -m spravomat.orchestration.process`  → grouping.run() → presentation.run()

Each sets up logging, calls the component `run()`s in order, is fail-fast on
`success=False`, and exits non-zero on failure (so Heroku logs it clearly).

## Dependency on db (new work)
- `delete_articles_older_than(days: int) -> dict` — deletes articles whose
  `fetched_at` is older than `days`; returns the standard dict with the number
  of rows deleted in `data`.

## Parked / open questions
- Alerting form (email / other) — parked.
