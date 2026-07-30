# Spravomat

Slovak lateral-reading news aggregator. Collects articles from Slovak news
outlets, clusters them by story, and shows which outlets cover each story.

## Structure

- `spravomat/acquisition` — fetch + normalize articles (RSS, scraping)
- `spravomat/grouping` — cluster articles into stories
- `spravomat/presentation` — rank stories + LLM enrichment
- `spravomat/db` — database access layer
- `spravomat/orchestration` — pipeline scheduling
- `spravomat/shared` — config, logging
- `spravomat/web` — Flask web app

## Setup

```bash
pip install -e .
cp .env.example .env   # then fill in values
```

## Run

```bash
python -m spravomat.db.migrations # create/update the database schema
python -m spravomat.acquisition   # 1. fetch + store articles (all sources)
python -m spravomat.grouping      # 2. cluster articles into stories
python -m spravomat.presentation  # 3. rank stories into display-ready cards
flask --app spravomat.web run     # 4. serve the page at http://127.0.0.1:5000
```

In production the pipeline steps are run on a schedule by orchestration, not
by hand (see [Orchestration](#orchestration)):

```bash
python -m spravomat.orchestration.collect  # hourly: acquisition + retention
python -m spravomat.orchestration.process  # 3x/day: grouping + presentation
```

## Deployment

Runs on a single Hetzner VPS via Docker Compose: `db`, `web`, and `caddy` (the
HTTPS edge) stay up; `batch` is run-only, invoked on a schedule by host cron.
Full setup, memory notes, and the DBeaver access guide live in
[`plans/deploy.md`](plans/deploy.md) and [`plans/db.md`](plans/db.md).

## The pipeline

Four data components run in order, each reading the previous one's output from
the database and writing its own. The database is the only thing they share —
no component imports another's internals.

```
acquisition ─► articles ─► grouping ─► article_clusters ─► presentation ─► story_cards ─► web
  (RSS)                     (embed +                        (rank + build
                             cluster)                        story cards)
```

## Data acquisition

Fetches articles from Slovak news outlets, normalizes them into one schema, and
stores them in the `articles` table (the single source of truth). It runs four
phases in order, fail-fast:

```
FETCH  ─►  DEDUP  ─►  ENRICH  ─►  STORE
(RSS)     (drop URLs   (scrape the   (insert into
          we already   lead paragraph  Postgres)
          have)        = perex)
```

Dedup runs **before** enrich on purpose: perex scraping is slow (one web request
+ a short pause per article), so we only scrape articles that are actually new.
The first run is slow (everything is new); later runs only scrape a handful.

### `summary` vs `perex`

Both are "the lead text of an article", but they come from different places:

- **`summary`** — comes free from the RSS feed. Present for ~99% of articles.
- **`perex`** — scraped from the article's own web page (the ENRICH phase).
  Best-effort: `None` if the outlet is unsupported or the scrape fails.

We currently scrape `perex` for **every** new article. In practice this is
largely redundant: for most outlets the RSS `summary` already contains the same
lead text (identical, or richer). Measured on a full run, `summary` was the
same as or better than `perex` for the large majority of articles, and perex
scraping is the main reason the first run takes minutes.

Kept as-is for now (both fields stored). **Future optimization:** switch to a
fallback model — use `summary` as the lead and scrape `perex` only when
`summary` is missing or too short. That would cut a full run from minutes to
seconds with little quality loss. Not done yet; noted here so the trade-off
isn't forgotten.

Files (each has one job):

- `acquisition/sources.py` — declarative spec per source (feed URLs + how that
  source exposes image/category). Just data.
- `acquisition/rss.py` — one generic loop that fetches every feed and turns RSS
  into `Article` objects, applying each source's strategies.
- `acquisition/perex.py` — scrapes the lead paragraph from each article page
  (per-site; best-effort — a failure just leaves `perex` empty).
- `acquisition/runner.py` — `run()`, the entry point that orders the four phases.
- `shared/models.py` — the `Article` shape shared with `db`.
- `db/repository.py` — `get_existing_urls` (dedup) and `save_articles` (store).

## Adding a news source

Common case: **add one entry to `SOURCE_SPECS` in `acquisition/sources.py`** —
nothing else changes.

```python
SourceSpec(
    medium="example",                                  # canonical key, stored on every article
    feeds={None: "https://example.sk/rss"},            # {category_label_or_None: feed_url}
    image_strategy="media_content",                    # see options below
    category_strategy="from_tags",                     # see options below
)
```

First, peek at one real feed entry to see where the image/category live:

```bash
.venv/bin/python -c "import feedparser; e=feedparser.parse('FEED_URL').entries[0]; \
print(sorted(e.keys())); print('media_content=', e.get('media_content')); \
print('thumbnail=', e.get('thumbnail')); print('tags=', e.get('tags'))"
```

Then pick the matching strategy:

| where the image is | `image_strategy` |
|---|---|
| `entry.media_content[0].url` | `"media_content"` |
| `entry.thumbnail` | `"thumbnail"` |
| `entry.image_url` | `"image_url"` |
| typed image in `entry.links` | `"links_by_type"` |
| no image | `"none"` |

| where the category is | `category_strategy` |
|---|---|
| the feeds-dict label (multi-category source) | `"from_feed_key"` |
| `entry.tags[0].term` | `"from_tags"` |
| first path segment of the URL | `"from_path"` |
| no category | `"none"` |

Extra steps, only if needed:

- **New image/category shape** not in the tables above → add one branch to
  `_extract_image` / `_extract_category` in `acquisition/rss.py`, then use its
  name in the spec.
- **Feed blocks the default client** (403) → set `use_headers=True`.
- **Want perex for it** → add a per-site method in `acquisition/perex.py` and
  register its domain in `self._scrapers`. Skip this and `perex` stays empty
  (fine — it's nullable).
- **Feed is temporarily blocked** but you want to keep the spec → set
  `known_blocked=True` so an empty result logs calmly instead of as a warning.

## Grouping

Turns articles into stories: articles about the same event are clustered
together. This is the heart of the product — lateral reading means seeing the
same event across many outlets.

```
read all articles ─► embed ─► similarity ─► cluster ─► score ─► drop weak ─► write mapping
```

- Each article's text (title + summary + perex) is embedded with a language
  model (`bge-m3`), and similar articles are clustered together.
- Each article gets a confidence score; weakly-connected ones are dropped.
- Output is a plain `article_id → cluster_id` mapping in the `article_clusters`
  table. Cluster ids are **rebuilt from scratch each run** — they are not stable
  across runs.
- All the clustering internals (model, thresholds, scoring) are hidden inside
  grouping. The rest of the app only ever sees the mapping.

Note: the model (`bge-m3`) is heavy. It is imported lazily, so importing
grouping is cheap — the model loads only when clustering actually runs.

Files: `grouping/clusterer.py` (the engine), `grouping/config.py` (model +
thresholds), `grouping/runner.py` (`run()`).

## Presentation

Turns clusters into ranked, display-ready **story cards**.

```
read mapping + articles ─► aggregate to clusters ─► keep >=2 media
─► rank ─► take top N ─► build cards ─► write story_cards
```

- Keeps only clusters covered by **2+ outlets** (real lateral reading — this
  also drops the single-outlet clusters grouping produced).
- Ranks by size + media count + freshness, keeps the top N (default 15).
- Each card is **self-contained**: title, sources (outlet + title + url), image,
  and counts are all baked in, so the web layer just renders — no joins.
- **Enrichment** (title + bullets) sits behind a swappable `Enricher` interface:
  - Default: **Gemini** reads each story's articles (title + summary + perex) and
    writes a Slovak title plus bullets, drawing concrete facts from the text and
    nothing else (strictly no outside knowledge, so bullets stay verifiable
    against the linked sources).
  - Fallback: a keyword title (from the articles) with no bullets — used per card
    if the LLM call fails, and for the whole run if `GEMINI_API_KEY` is unset. The
    app always works without an LLM.
  - No cache: enrichment is recomputed each run, so titles/bullets may vary
    between runs (accepted for now).

Files: `presentation/ranking.py` (aggregate + rank), `presentation/enrichment.py`
(`Enricher` interface, `GeminiEnricher`, keyword fallback, `get_enricher()`),
`presentation/prompts.py` (the Slovak prompt), `presentation/cards.py` (assemble
cards), `presentation/config.py` (knobs), `presentation/runner.py` (`run()`).

## Web

The dumb-render layer: reads the finished story cards and renders one HTML page.
No business logic, no joins, no data decisions — everything is already baked into
the cards by presentation.

- ONE route (`/`) → `get_story_cards()` → render. Nothing else is read.
- The **only** thing web computes is relative time (`pred 3 h`) from each card's
  timestamp, in Bratislava time — presentation relative to the moment of viewing.
- Server-rendered Flask + Jinja, no JS framework. Flask application factory
  (`create_app()`), so `gunicorn "spravomat.web:create_app()"` serves it in the
  `web` container, with Caddy as the HTTPS edge in front.

Run it locally with `flask --app spravomat.web run` and open
http://127.0.0.1:5000.

Files: `web/__init__.py` (`create_app()` factory), `web/routes/` (the `/` route),
`web/filters.py` (relative-time + outlet-label Jinja filters), `web/templates/`
(base + home + navbar + footer), `web/static/css/main.css`.

## Orchestration

Runs the pipeline steps in order, on a schedule. It adds no new logic — it just
calls the components' `run()` functions as black boxes, in order, stopping at the
first failure (fail-fast). Split into two runs by how often they need to happen:

```
collect  (hourly)   →  acquisition.run()  →  retention (delete > 3 days old)
process  (3x/day)   →  grouping.run()     →  presentation.run()
```

- **Collection is frequent** because RSS feeds roll fast — miss a window and
  articles are gone. **Processing is not** — clusters/cards only need refreshing
  a few times a day (06:00 / 12:00 / 18:00 UTC; night off).
- **Retention** deletes articles older than 3 days (by `fetched_at`), keeping the
  data fresh and bounding how much grouping has to cluster. `ON DELETE CASCADE`
  cleans up the cluster rows automatically.
- Thanks to dedup-before-enrich, steady-state `collect` is fast (only new
  articles get scraped) — e.g. 581 fetched but only ~25 new → ~40s.

Scheduling uses **host cron** on the VPS as a dumb trigger: one hourly job for
`collect` (at :30), and three daily jobs (05/11/19 UTC) for `process`. Each job
just runs
`docker compose run --rm batch python -m spravomat.orchestration.<collect|process>`
under a shared `flock`, so collect and process can never overlap (RAM guard);
all the order/fail-fast logic lives in the scripts.

A fourth cron job takes a daily `pg_dump` at 03:10 UTC — see
[`plans/backup.md`](plans/backup.md).

Files: `orchestration/__init__.py` (`run_steps` — the shared fail-fast helper),
`orchestration/collect.py` and `orchestration/process.py` (the two entry points).