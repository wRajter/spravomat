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
flask --app spravomat.web run     # web app
python -m spravomat.db.migrations # create/update the database schema
python -m spravomat.acquisition   # fetch + store articles (all sources)
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