# Plan — acquisition

## Purpose
Fetch articles from Slovak news outlets and normalize them into one unified
schema, then store them in the articles table (the single source of truth).
Output is always the unified schema, regardless of source type.

## Responsibilities
- Fetch from two source types: RSS feeds and web scraping (for perex when the
  feed lacks it).
- Normalize different source formats into the fixed core schema.
- Write normalized articles to the articles table.

## Out of scope
- Retention / deleting old articles → that is a separate orchestration step.
- Clustering, scoring → grouping component.

## Contract (output)
Each article written to the articles table has:
- `article_id` (primary key, used for all later joins)
- Core fields (every source must provide these): title, url, medium,
  published_at, summary, perex
- Free attributes (JSONB) for optional/future fields (e.g. author, category)

## Design notes
- Adding a new source will never be fully trivial, but common logic (fetch →
  normalize → store) must be generalized so per-source code is minimal.
  Per-source code = only what differs (field mapping, date format, how to reach
  perex).
- Perex scraping is per-source and fragile (each site differs). Reference the
  POC's approach but aim to make it as maintainable as possible.

## Reference (POC — spravomat-poc repo)
- `scrapers/rss_extractor.py` — RSS fetching + normalization
- `scrapers/perex_scraper.py` — per-source perex scraping
- POC sources: SME, Aktuality, Denník N, Teraz.sk, SITA, 24hodín, Euractiv,
  Košice Dnes

## Open questions
- Which parts of a new source are config (feed URL, field mapping) vs code
  (scraping logic)? Decide the split when building.

---

# Claude's review (2026-07-15)

Overall: the plan is solid and consistent with the architecture. Moving
retention out to orchestration is the right call (POC mixed cleanup into
extraction). Below are the gaps I found and the decisions I need from you.
Answer inline under each question (e.g. `A:` lines). No code until these
are resolved.

## Gaps in the plan (my findings)

1. **`article_id` is undefined.** It is the join key for the whole pipeline,
   but the plan never says how it is generated. The POC has no real ID — it
   dedupes on URL, then title. This must be decided here because grouping and
   presentation depend on it.

2. **Deduplication is not mentioned.** The POC does real dedup (URL first,
   then title). That is genuine acquisition logic and cannot just disappear.
   Needs a home (acquisition vs the db write layer).

3. **`image_url` is missing from the contract.** Story cards need an image
   (presentation contract), and every POC source extracts one, yet it is not
   in the core fields. Must be placed: core field or JSONB attribute.

4. **"perex" as a required core field contradicts reality.** Perex is scraped
   best-effort and is often `None` (unsupported media, failed scrape). It
   cannot be "every source must provide". It is core-but-nullable / best-effort.

5. **`published_at_str` should not exist.** POC stores a Slovak-formatted
   string next to the timestamp. In the new design, formatting is `web`'s job
   (dumb rendering). Store only the timestamp.

6. **"Two source types" framing is slightly misleading.** RSS is the article
   source (discovery + core fields). Perex scraping is a second enrichment pass
   over already-known URLs — it produces no new articles, only fills one field.
   Suggest reframing acquisition as: fetch (RSS) -> enrich (perex) -> store.
A: Agreed. Reframe acquisition as three sequential phases:
  fetch (RSS) -> enrich (perex) -> store
- fetch: RSS is the only source of new articles (discovery + core fields).
- enrich: perex scraping is a second pass over already-known URLs; it creates
  no new articles, only fills the perex field (best-effort).
- store: write normalized articles to the articles table.
RSS and perex are NOT two peer source types — RSS discovers, perex enriches.


## POC assessment (what to reuse vs rebuild)

- **`perex_scraper.py` — reuse, mostly fits.** Clean dispatch (domain->method),
  generic `_fetch_page`/`_extract_text` helpers, per-source methods hold only
  the differing CSS selector. Close to the pattern the plan wants.
- **`rss_extractor.py` — rebuild, do NOT port.** It is exactly the anti-pattern
  the plan warns against: one ~30-line method per source, ~80% copy-paste, only
  2-3 lines actually differ (image, category). Redesign as: a small per-source
  spec + one generic fetch->normalize loop.
- Other POC issues to avoid in the rebuild: columnar dict-of-lists output
  (use typed `Article` dataclasses instead); inconsistent `medium` keys
  (`euractiv_sk` vs `euractiv.sk`, misspelled `euroactiv`) — must be canonical
  and consistent, since the RSS<->perex join relies on them; no
  `{"success", "message", "data"}` return shape; fragile error handling
  (`_fetch_feed` returns None, caller then crashes); `kosicednes` scraper exists
  but the runner never calls it (plan lists 8 sources, POC runs 7).

## Questions I need you to answer

### Q1 — article_id generation
How should `article_id` be created?
  (a) DB auto-increment serial (simple, but ID only exists after insert)
  (b) Hash of the article URL (stable, deterministic, computable before insert,
      natural dedup key) — my recommendation
  (c) Something else
A: article_id = auto-increment integer, generated by the database. Deduplication is handled separately via a unique constraint on the article URL. The two are independent: id is the join key, URL is the dedup key.

### Q2 — deduplication: rule + location
Two parts.
  Rule — keep the POC's "dedup by URL, then by title"? Title-dedup drops two
  different articles that happen to share a headline across outlets, which for a
  lateral-reading product might be exactly what we want to KEEP. Reconsider?
A (rule):
  Location — where does dedup run: inside acquisition, or in the `db` write
  layer (e.g. insert-or-ignore on a unique URL/hash key)?
A (location):

A: Use the URL as the dedup key. Split into two parts:
a Mechanism (lives in `db`): a unique constraint on the article URL.
   The database guarantees no duplicate URL can be stored.
b Behavior (lives in `acquisition`): when a URL already exists, skip the
   article and continue with the next one.
Drop the POC's title-based dedup — URL dedup is sufficient for MVP.
Note: filtering near-identical articles across different outlets (syndication —
same content, different URLs, e.g. SITA/TASR wire copy) is a SEPARATE, PARKED
concern. It is content-similarity dedup, closer to the grouping stage, not URL
dedup. Do NOT implement it in acquisition.

### Q3 — image_url placement
Core field, or JSONB free attribute? (I lean core — presentation always wants
it.)
A: Core field, nullable. It belongs in core because story cards need it and every
source provides it — that is the criterion for core (needed downstream, commonly
present), unlike JSONB which is for optional/future fields (author, tags).
Nullable because some articles have no image or it fails to extract; downstream
handles a missing image by not showing one.

### Q4 — final core schema
Please confirm the exact core field list. My proposed set:
  `article_id, title, url, medium, published_at (timestamp),
   summary, perex (nullable), image_url`
  + `attributes` (JSONB) for the rest (author, category, ...).
Anything to add or remove?
A: Confirmed with two additions (category, fetched_at):
  article_id     -- auto-increment primary key, join key for the pipeline
  title
  url            -- unique constraint (dedup key)
  medium         -- canonical, consistent form across RSS and perex
  category       -- nullable (from RSS section; not all sources provide it)
  published_at   -- timestamp, when the article was published
  fetched_at     -- timestamp, when we stored it (our clock, for retention/debug)
  summary
  perex          -- nullable, best-effort
  image_url      -- nullable
  attributes     -- JSONB, for optional/future fields (author, tags, ...)
Notes:
- category is core-but-nullable. It may later move to a bigger role if
  blocking (cluster per category) is introduced — parked for now.
- medium must be canonical/consistent (the RSS<->perex join and media counts
  depend on it).


### Q5 — perex expectation
Confirm perex is core-but-nullable / best-effort (not guaranteed per source)?
A: Correct, drop it. Store only the timestamp (published_at). Formatting the date
for display is web's job (dumb rendering) — the database holds the fact (when
it was published), web decides how to show it. Storing a pre-formatted string
mixes presentation into data and duplicates it.
A: Correct. Perex is core but nullable / best-effort — not every source provides
it and scraping can fail. Same treatment as image_url: it's a core field that
may be empty. Downstream must handle a missing perex (e.g. grouping embeds from
whatever text is available — title, summary — when perex is absent).

### Q6 — config vs code split for a source (your original open question)
My proposal: a source = a small spec (medium key, feed URL(s), + how to pull the
source-specific bits like image/category) plus one shared generic loop.
Per-source code shrinks to only the differences. Perex keeps the POC's
method-per-domain dispatch (some sites need custom logic, e.g. 24hod split,
aktuality sport branch). Agree with this split?
A: Agreed. A source = a small spec (medium key, feed URL(s), how to pull
source-specific bits like image/category) + one shared generic loop. Per-source
RSS code shrinks to only the differences.
Keep the spec small and declarative (data + a few rules); all logic lives in
the generic loop. If logic starts leaking into the spec, that defeats the
purpose.
Perex correctly keeps the POC's method-per-domain dispatch — perex scraping
differs essentially per site (custom CSS, special cases like 24hod split), so
generalizing it would be artificial. Generalize where repetition is accidental
(RSS); keep specific where difference is essential (perex).

### Q7 — source list
Confirm the source list for v1. Plan lists 8 (SME, Aktuality, Denník N,
Teraz.sk, SITA, 24hodín, Euractiv, Košice Dnes). POC actually runs 7 (Košice
Dnes not wired). Include all 8, or match the POC's 7?
A: match the POC's 7

### Q8 — write path
Confirm acquisition writes only via `db` repository functions (no raw SQL, no
CSV). The POC's CSV persistence is dropped entirely, correct?
A: Confirmed, both points:
- CSV persistence from the POC is dropped entirely. All data goes to the
  database.
- Acquisition writes ONLY via `db` repository functions (e.g. save_articles).
  No raw SQL anywhere in acquisition. Acquisition must not know it's Postgres
  behind the interface — that's information hiding, so DB/schema changes stay
  contained in `db`.

---

# Follow-up questions (2026-07-15, round 2)

Your fetch -> enrich -> store reframing left one ordering decision open, plus a
minor field detail.

### Q9 — perex enrichment vs dedup ordering (IMPORTANT)
Perex scraping is the expensive, fragile part: one HTTP request per article
+ ~0.5s rate limit each. On an hourly cron, most RSS entries are DUPLICATES of
the previous run. If we enrich strictly before store ("fetch -> enrich ->
store"), we re-scrape perex for every already-stored article every hour — large
waste and extra load on the news sites.

Two ways to order it:
  (a) Dedup-first (my recommendation): fetch RSS -> ask `db` which URLs are new
      -> scrape perex ONLY for new URLs -> store complete rows in one insert.
      Cheapest; perex scraped exactly once per article. Slight nuance to the
      "enrich before store" framing (a dedup check precedes enrich), but store
      still happens last.
  (b) Store-then-enrich: fetch -> store new rows (perex empty) -> scrape perex
      for rows still missing perex -> UPDATE those rows. Matches the POC's
      two-pass flow, but needs an UPDATE path in `db` and writes each new
      article twice.
Which ordering?
A: Go with (a). Store each article once, complete, in a single insert. Scrape
perex only for new URLs (dedup check first). Simpler than (b) — no UPDATE path
needed.
Flow: fetch -> dedup -> enrich -> store.

### Q10 — fetched_at: who sets it?
  (a) DB default (`now()` server clock) when the row is inserted — my
      recommendation; keeps it out of acquisition, one source of truth.
  (b) Acquisition sets it explicitly before calling `db`.
A: Option (a). DB default (now()) sets fetched_at on insert. Keeps it out of
acquisition, one source of truth for the time.