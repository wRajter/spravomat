# CLAUDE.md — Spravomat

## What this is
Slovak lateral-reading news aggregator. Collects articles from Slovak news
outlets, clusters them into stories, ranks stories, and displays which outlets
cover each story. Batch pipeline + read-only web frontend.

## How to work on this project
- The user makes all decisions. Propose, don't decide. Wait for confirmation
  before building.
- POC lives in the separate `spravomat-poc` repo. It is a REFERENCE, not a
  template. Do not port its structure. Build fresh per the architecture below.
- Detailed per-component plans live in `plans/`. Read the relevant one before
  building a component.

## Architecture principles (hard rules)
- Separation of Concerns, Single Responsibility, Low Coupling, High Cohesion.
- Information Hiding: each component hides its internals behind a contract.
  Other components know only the contract, never the internals.
- KISS: prefer the simplest solution that works.
- Contracts between components are stable. Changing a component's internals
  must not affect others.

## The six components
1. `acquisition` — fetch + normalize articles (RSS, scraping) into one schema.
2. `grouping` — cluster articles into stories (embeddings + clustering + scoring).
3. `presentation` — rank stories, LLM-enrich top ones into story cards.
4. `web` — Flask app. Dumb rendering only, no business logic.
5. `db` — database access layer (repository functions, schema, migrations).
6. `orchestration` — runs the pipeline steps in order (fail-fast). Two runs:
   `collect` (acquisition → retention; frequent) and `process` (grouping →
   presentation; a few times a day).
Plus `shared` — config, logging (cross-cutting).

## Contracts (data flowing between components)
- acquisition → articles table (SINGLE SOURCE OF TRUTH). Each article has an
  `article_id` (primary key, used for all later joins) + core fields
  (title, url, medium, published_at, summary, perex) + free attributes (JSONB).
- grouping → `article_id → cluster_id` only (POOR CONTRACT). Confidence score
  stays internal. Uncategorized articles are not passed on.
- presentation → story cards (title, bullets, sources, image, counts).
  Denormalized, ready to render.
- Downstream joins back to the articles table via `article_id` for extra data.

## Three kinds of data (never mix)
1. Pipeline data — live, lean, short retention. The product.
2. Internal state — grouping's private embeddings/model. Hidden inside grouping.
   May not be SQL. Not part of any contract.
3. Observability — logs/audit. Outside the pipeline. Pipeline never reads them.

## Key decisions
- Database: PostgreSQL. Access only via `db` repository functions, never raw SQL
  elsewhere.
- Schema defined in code (migrations), so local and prod DBs stay identical.
- LLM provider: Gemini (`google-genai`), used for batch enrichment. OpenAI /
  Anthropic keys appear only in throwaway comparison tests, not the pipeline.
- Hosting: Docker Compose on a Hetzner VPS (`db`, `web`, `caddy` always up;
  `batch` run-only). Caddy is the HTTPS edge. Keep the core platform-neutral —
  platform-specific things (connection string, scheduler) live at the edge in
  `shared` config. See `plans/deploy.md`.
- Local dev uses a local database; production uses the `db` Postgres container
  on the VPS. Switch only via the DATABASE_URL environment variable, never in
  code. For DBeaver access to the prod DB, see `plans/db.md`.

## Parked decisions (do NOT implement — open until decided)
- batch vs online clustering (waits on measurement)
- enrichment cache strategy
- alerting form
- delivery interactivity scope

## Coding conventions
- All code, comments, docstrings in English.
- Functions return `{"success": bool, "message": str, "data": ...}`.
- Always try/except. Docstrings + type hints. File path as first-line comment.
- Readability and clarity are top priority. Code should be easy to read and
  understand. Prefer clear, obvious code over clever code.
- Use OOP where it fits the problem; avoid over-engineering (no unnecessary
  layers or abstractions). Keep it simple.
- Prefer flat/procedural over deep nesting.