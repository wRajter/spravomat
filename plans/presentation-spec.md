# Spec — presentation (finalized)

> Authoritative spec to build against. Consolidates the decisions made in
> `presentation.md` (kept as reference + full Q&A rationale). Finalized
> 2026-07-16.

## Purpose
Turn clusters into ranked, display-ready story cards. Read the grouping output
(`article_id -> cluster_id`) and the articles, aggregate to clusters, keep only
lateral-reading stories (>=2 media), rank them, take the top N, and write
finished, self-contained story cards for the web to render.

## v1 scope — NO LLM yet
Build presentation WITHOUT the LLM first: ranking + card assembly + keyword
titles, verified end-to-end producing real cards. The LLM provider is slotted in
later behind the `enrich()` interface, once chosen (parked, isolated).

Consequence for v1: every card's title is the TF-IDF keyword title (a joined
keyword string, e.g. "messi, argentína, anglicko") and bullets are empty. The
keyword/empty-bullets path is BOTH the v1 default and the permanent LLM-failure
fallback.

## Pipeline (what a run does)
```
read mapping + articles (db) -> aggregate to clusters -> filter (>=2 media)
-> rank -> take top N -> build cards (keyword title; LLM later) -> write cards (db)
```

## Contract
- **Input**: `article_id -> cluster_id` from grouping (db) + articles from db,
  joined via `article_id` for medium/date/title/url/image.
- **Granularity change**: per-article -> per-cluster (aggregation).
- **Filter**: keep only clusters with `>= 2` media (lateral reading). This also
  removes the singletons grouping produced — they never reach the page.
- **Output**: top N finished story cards. SELF-CONTAINED — presentation bakes
  everything the page needs into the card at build time. Web reads ONLY
  `story_cards`, performs NO joins. (This intentionally overrides the general
  "downstream joins back via article_id" note, for the web layer specifically.)
- Persisted in db as pipeline data, full-replace each run.

## Story card shape (fields baked in)
- `cluster_id`     — ephemeral batch id (identifier for the card)
- `title`          — keyword title for v1 (LLM title later)
- `bullets`        — empty for v1 (LLM bullets later); JSONB list
- `sources`        — JSONB list of {medium, title, url}, one per article
- `image_url`      — first available image across the cluster's articles, or None
- `media_count`    — distinct media in the cluster
- `article_count`  — articles in the cluster
- `newest_at`      — newest article's published_at
- `rank_score`     — the score used to order cards (for display / debugging)

## Ranking (POC values carried as-is for v1)
Per-cluster `rank_score = size + media + freshness`:
- `size = min(article_count, 10)`
- `media = media_count * 3` (heaviest weight — lateral reading is the core signal)
- `freshness` by newest-article age: `<6h -> 5, <24h -> 3, <48h -> 1, else 0`
Sort descending, take top N. `N = 15` (arbitrary for testing; in
`presentation/config.py`, tunable, likely raised later).

## Keywords (computed here, carried from POC)
- Carry `_extract_cluster_keywords` (TF-IDF over cluster article titles) +
  `SK_STOP_WORDS`. Moved here because grouping no longer computes keywords.
- The keyword title = the top keywords joined into a string. Used as the v1
  title and as the LLM-failure fallback.

## Enrichment (LLM) — interface now, provider later
- HIDDEN behind an interface: `enrich(cluster) -> {title, bullets}`. Which
  provider/model is an implementation detail, swappable without touching the
  rest of presentation.
- Provider/model config lives in `presentation/config.py`; the API key lives in
  `.env` (secret, read from environment).
- v1 ships WITHOUT a concrete provider — the interface exists, cards fall back to
  keyword titles + empty bullets. When a provider is added, only the top N cards
  are enriched.
- On LLM failure (later): keyword title + empty bullets, so the card still
  renders.
- Provider choice (OpenAI / Gemini / Claude) is PARKED — decide with a current
  cost/quality check when building the concrete enricher.
- v1: NO cache. Enrichment (once added) recomputed each run. Titles/bullets may
  change between runs — accepted tradeoff. Stable story identity + caching is a
  separate parked high-priority task.
- Enrichment input fields (titles only vs + perex/summary) — parked.

## Dependency on `db` (new work presentation requires)
- **Read**: reuse `get_all_articles()`; add a reader for the mapping, e.g.
  `get_cluster_mapping() -> {article_id: cluster_id}` (or a joined read). Confirm
  exact shape in module design.
- **Write**: new table `story_cards` + a repository function that full-replaces
  the previous run's cards in one transaction (same pattern as
  `article_clusters`).
  ```sql
  CREATE TABLE IF NOT EXISTS story_cards (
      cluster_id    INTEGER PRIMARY KEY,
      title         TEXT NOT NULL,
      bullets       JSONB NOT NULL DEFAULT '[]'::jsonb,
      sources       JSONB NOT NULL DEFAULT '[]'::jsonb,
      image_url     TEXT,
      media_count   INTEGER NOT NULL,
      article_count INTEGER NOT NULL,
      newest_at     TIMESTAMPTZ,
      rank_score    INTEGER NOT NULL,
      created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
  );
  ```
  DB (not a JSON file) because Heroku's filesystem is ephemeral, and to stay
  consistent with the rest of the pipeline. JSONB is a column type inside the
  table, not a separate file.
- Presentation never touches SQL directly — only these repository functions.

## Carry vs leave (from POC)
Carry:
- `ClusterRanker` (aggregate, filter >=2 media, rank_score, sort)
- TF-IDF keyword extraction (moved here from grouping)
- `ClusterEnricher` shape — but behind an interface, and NOT wired in v1
Leave / change:
- cache-by-cluster_id logic (`run_post_clustering.py`) — DROPPED for v1
- CSV persistence -> db
- top-N cap belongs here (ranking), not in web (web is dumb render)
- web re-joining articles per cluster — REMOVED; cards are self-contained

## Parked (do NOT implement / decide now)
- enrichment cache + stable story identity (separate high-priority task)
- LLM provider choice (decide when building the concrete enricher)
- enrichment input fields (titles only vs + perex)
- near-identical/syndication dedup (belongs near grouping)

## Open questions (for later)
- exact mapping-read shape (confirm in module design)
- when the LLM is added: provider, model, prompt, input fields
