# Spec — acquisition (finalized)

> Authoritative spec to build against. Consolidates the decisions made in
> `acquisition.md` (which is kept as reference + full Q&A rationale).
> Finalized 2026-07-15.

## Purpose
Fetch articles from Slovak news outlets, normalize them into one unified schema,
and store them in the `articles` table (the single source of truth). Output is
always the unified schema, regardless of source.

## Flow (three phases + a dedup check)
```
fetch (RSS) -> dedup -> enrich (perex) -> store
```
- **fetch** — RSS is the only source of new articles (discovery + core fields).
- **dedup** — ask `db` which of the fetched URLs are new; drop the rest. This
  precedes enrich so we never scrape perex for articles we already have.
- **enrich** — scrape perex only for the new URLs (best-effort; may be `None`).
- **store** — write each new article once, complete, via `db`.

RSS and perex are NOT two peer source types: RSS discovers, perex enriches.

## Responsibilities
- Fetch and parse RSS feeds for the configured sources.
- Normalize each source's format into the fixed core schema.
- Ask `db` which fetched URLs are new (dedup check).
- Scrape perex for new articles only (best-effort enrichment of one field).
- Hand normalized articles to `db` for storage.

## Out of scope
- Retention / deleting old articles → separate orchestration step.
- Clustering, scoring → grouping component.
- Content-similarity / syndication dedup (same story, different URLs, e.g.
  SITA/TASR wire copy) → PARKED; belongs near grouping, not here.

## Contract (output)
Each article written to the `articles` table:

| field         | type      | notes                                             |
|---------------|-----------|---------------------------------------------------|
| `article_id`  | serial PK | DB auto-increment; join key for the whole pipeline|
| `title`       | text      |                                                   |
| `url`         | text      | UNIQUE — the dedup key                            |
| `medium`      | text      | canonical, consistent across RSS + perex          |
| `category`    | text/null | not all sources provide it                        |
| `published_at`| timestamp | when the article was published (source's time)    |
| `fetched_at`  | timestamp | when we stored it; DB default `now()`             |
| `summary`     | text      | from RSS                                           |
| `perex`       | text/null | best-effort scrape; may be absent                 |
| `image_url`   | text/null | best-effort; downstream shows none if absent      |
| `attributes`  | JSONB     | optional/future fields (author, tags, ...)        |

Core = needed downstream and commonly present. JSONB = optional/future.
Downstream joins back to this table via `article_id`.

## Key decisions (resolved)
1. **article_id** — DB auto-increment integer. Independent of dedup: `id` is the
   join key, `url` is the dedup key.
2. **Dedup** — key is `url`. Mechanism: UNIQUE constraint on `url` in `db`
   (hard guarantee). Behavior: acquisition checks which URLs are new and skips
   existing ones. Title-based dedup from the POC is dropped.
3. **image_url** — core field, nullable.
4. **perex** — core field, nullable, best-effort. Downstream must handle its
   absence (e.g. grouping embeds from title/summary when perex is missing).
5. **No `published_at_str`** — store only the timestamp; formatting is `web`'s
   job (dumb rendering).
6. **fetched_at** — set by DB default `now()`, not by acquisition.
7. **Perex ordering** — dedup-first: scrape perex only for new URLs; each
   article stored once, complete (no UPDATE path needed).

## Design — RSS: spec + generic loop
Adding a source must stay near-trivial. Generalize the accidental repetition,
keep only the essential differences per source.

- A **source** = a small, declarative **spec**: `medium` key, feed URL(s), and a
  few rules for the source-specific bits (how to reach image / category).
- **One generic loop** does the common work: fetch feed -> extract common fields
  (title, url, summary, published_at) -> apply the spec's per-source rules ->
  build a typed `Article`.
- Keep specs data-only. If logic starts leaking into a spec, that defeats the
  purpose — it belongs in the loop.
- Output is a list of typed `Article` objects (dataclass), NOT the POC's
  columnar dict-of-lists.

## Design — perex: per-domain dispatch (reuse from POC)
- Keep the POC's `perex_scraper.py` shape: domain -> method dispatch, generic
  `_fetch_page` / `_extract_text` helpers, per-source methods holding only the
  differing CSS selector / special case (e.g. 24hod paragraph split,
  aktuality sport branch).
- Perex differs essentially per site, so generalizing it would be artificial.
  Generalize where repetition is accidental (RSS); stay specific where the
  difference is essential (perex).

## Sources (v1 — 7)
SME, Aktuality, Denník N, Teraz.sk, SITA, 24hodín, Euractiv.
(Košice Dnes from the plan is dropped for v1 — the POC never wired it.)

## Conventions & constraints
- Write path: `db` repository functions ONLY (e.g. `save_articles`). No raw SQL
  and no CSV anywhere in acquisition. Acquisition must not know it is Postgres
  behind the interface (information hiding).
- `medium` keys must be canonical and consistent — the RSS<->perex join and the
  media counts depend on them. Fix the POC's inconsistencies
  (`euractiv_sk` vs `euractiv.sk`, misspelled `euroactiv`).
- Standard return shape `{"success": bool, "message": str, "data": ...}`.
- try/except around I/O and parsing; log failures. Docstrings + type hints.
  All code/comments in English.

## Dependency on `db` (interface acquisition needs)
Acquisition assumes `db` provides (exact names TBD when building `db`):
- a way to find which of a set of URLs already exist (dedup check), and
- a way to store a batch of normalized articles (insert, skipping existing URLs).
The `articles` table schema (above) and the UNIQUE constraint on `url` live in
`db` migrations.
