# Plan — db

## Purpose
The only component that talks to PostgreSQL. Everyone else calls repository
functions and never sees SQL or psycopg. `db` owns the schema and hides storage
entirely (Information Hiding): the rest of the app knows the repository
contract, never the internals.

## Responsibilities
- Define the database schema (in code) and create it (idempotently).
- Manage the database connection.
- Provide repository functions — the only way in and out of the database.

## Out of scope
- Business logic (dedup rules, ranking, clustering) → lives in the components
  that own it. `db` only mechanically stores/reads and enforces the UNIQUE(url)
  constraint.
- Retention / deleting old rows → an orchestration step (may call a repository
  delete function later; not built now).

## Dependencies
- `shared.config` — for `DATABASE_URL` (scoped as part of this work; see below).
- `shared.models` — for the `Article` dataclass (write shape).
- Depends on nothing else. Dependency direction stays clean (acquisition → db →
  shared).

## Contract (repository functions)
All repository functions return the standard dict
`{"success": bool, "message": str, "data": ...}`, wrap SQL in try/except, and
log failures with `logging.error`.

v1 provides the two functions acquisition needs:

- `get_existing_urls(urls: list[str]) -> dict`
  `SELECT url FROM articles WHERE url = ANY(%s)`.
  `data` = `set[str]` of URLs already stored. Short-circuits to an empty set if
  `urls` is empty (no query). Used by acquisition's dedup phase.

- `save_articles(articles: list[Article]) -> dict`
  Batch `INSERT ... ON CONFLICT (url) DO NOTHING` (the safety net against
  concurrent runs). `data` = number of rows actually inserted (`cursor.rowcount`).
  `attributes` is passed as JSONB via psycopg's `Jsonb` wrapper. `article_id`
  and `fetched_at` are left to the database.

Reader functions (for grouping/presentation) are added later when those
components need them — not part of v1.

## Schema — `articles` table
Single source of truth. Matches the acquisition contract exactly.

```sql
CREATE TABLE IF NOT EXISTS articles (
    article_id   BIGSERIAL PRIMARY KEY,            -- pipeline join key
    title        TEXT        NOT NULL,
    url          TEXT        NOT NULL UNIQUE,       -- dedup key
    medium       TEXT        NOT NULL,
    category     TEXT,                              -- nullable
    published_at TIMESTAMPTZ,                       -- nullable (some feeds omit it)
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    summary      TEXT,
    perex        TEXT,                              -- nullable, best-effort
    image_url    TEXT,                              -- nullable
    attributes   JSONB       NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles (published_at);
```

- Index on `published_at` only for v1 (retention + ranking query by it). A
  `medium` index is PARKED until media-count queries prove slow.

## Key decisions (resolved)
1. **Schema definition + migrations — idempotent DDL, no versioned runner.**
   The schema DDL uses `CREATE TABLE / INDEX IF NOT EXISTS` and is re-run each
   release. KISS: one table, no history yet. Versioned migrations (numbered
   files + a `schema_migrations` tracking table) are added LATER, when the first
   real schema change makes the idempotent approach awkward. Entry point stays
   `python -m spravomat.db.migrations` (Procfile `release`), now just applying
   the idempotent DDL.
2. **Timezones — `TIMESTAMPTZ` + UTC-aware datetimes.** Store unambiguous UTC
   instants; the web layer renders Bratislava time later. This requires an
   acquisition fix: `rss.py` must emit UTC-aware datetimes
   (`datetime(*published_parsed[:6], tzinfo=timezone.utc)`) — feedparser gives
   UTC but currently we build naive datetimes. This is the same timezone bug
   class found in the POC.
3. **Connection — one connection per operation, pooling parked.** A thin
   `connection()` context manager opens a psycopg 3 connection from
   `DATABASE_URL`, commits on clean exit, rolls back on exception. Fine for a
   batch pipeline + low-traffic read-only web. Pooling is a future optimization.
4. **`models.py` — stub for now.** With raw SQL (no ORM) and the write-shape
   `Article` living in `shared`, `db/models.py` has no job yet. Reserved for
   read-side row→object mapping when the first reader needs full rows (with
   `article_id`, `fetched_at`).

## shared.config (scoped here)
`db` cannot read `DATABASE_URL` without it, so it is built alongside `db`.
- Loads `.env` via python-dotenv (local dev; on Heroku the env is already set).
- Exposes at least `DATABASE_URL`, plus `LOG_LEVEL`, `DEBUG` (from `.env.example`).
- Platform-neutral: the only platform-specific value is `DATABASE_URL`, which
  switches local vs prod purely via the environment variable, never in code.
- Keep it simple (module-level constants read after `load_dotenv()`); a
  `Settings` dataclass is an option if it reads more cleanly when built.

## File layout
```
spravomat/db/
├── __init__.py              # empty for now (callers import from db.repository)
├── connection.py            # connection() context manager (uses shared.config)
├── models.py                # stub (reserved for read models)
├── repository.py            # get_existing_urls, save_articles
└── migrations/
    ├── __init__.py          # SCHEMA_DDL + init_schema() applying it idempotently
    └── __main__.py          # entry point: python -m spravomat.db.migrations

spravomat/shared/
└── config.py                # DATABASE_URL, LOG_LEVEL, DEBUG (dotenv-loaded)
```

## Build order
1. `shared/config.py` (prerequisite — provides `DATABASE_URL`).
2. `connection.py` (needs config).
3. `migrations/` (schema DDL + runner; verify table is created locally).
4. `repository.py` (`get_existing_urls`, `save_articles`).
5. Acquisition follow-up: the `rss.py` UTC-aware datetime fix (decision 2).

## Open questions
- Local Postgres: is a local DB already running / created
  (`spravomat_dev` per `.env.example`), or do we set that up as part of testing
  the migration + repository step?

## Connecting to the production DB from DBeaver (Mac)
The prod DB runs in Docker on the VPS. It is NOT exposed to the internet — the
`db` service binds its port to `127.0.0.1:5432` (host-only). Reach it from
DBeaver on your Mac through an SSH tunnel.

Server side (already done, one-time):
- `docker-compose.yml` `db` service has:
  ```yaml
  ports:
    - "127.0.0.1:5432:5432"
  ```
- Apply with `docker compose up -d db`; verify `docker compose ps` shows
  `127.0.0.1:5432->5432/tcp`.

DBeaver connection (New PostgreSQL connection):
- **SSH tab** → Use SSH Tunnel:
  - Host/IP: VPS IP (e.g. `178.105.1.59`), Port: `22`
  - User: `lubomir`
  - Auth: Password (SSH-key auth failed with "Exhausted available
    authentication methods" — key on the server didn't match; password works).
- **Main tab** (as seen from *inside* the server, via the tunnel):
  - Host: `localhost`, Port: `5432`
  - Database / Username / Password: the `POSTGRES_*` values from server `.env`.
- Test Connection → Finish. Reconnecting later just reopens the tunnel
  automatically.
