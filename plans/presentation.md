# Plan — presentation

## Purpose
Turn clusters into ranked, display-ready story cards. Takes the grouping output
(article_id -> cluster_id) and the articles, ranks the stories, LLM-enriches the
top ones (title + bullets), and outputs finished story cards for the web to
render.

## Contract
- Input: article_id -> cluster_id from grouping (in db) + articles from db
  (source of truth, joined via article_id for medium/date/title/image).
- Granularity change (first step): per-article -> per-cluster (aggregation).
- Filter: keep only clusters with >= 2 media (lateral reading). This also
  removes the singletons grouping produced — they never reach the page.
- Output: finished story cards — title, bullets, sources (medium + article
  title + url), image_url, media_count, article_count, newest_at. Denormalized,
  ready to render. Persisted in db as pipeline data.

## Pipeline (what a run does)

read mapping + articles (db) -> aggregate to clusters -> filter (>=2 media)
-> rank -> take top N -> LLM-enrich top N -> write story cards (db)

## Ranking (POC values carried as-is for v1)
Per-cluster rank_score = size + media + freshness:
- size = min(article_count, 10)
- media = media_count * 3 (heaviest weight — lateral reading is the core signal)
- freshness = newest article age (<6h -> 5, <24h -> 3, <48h -> 1, else 0)
Sort descending, take top N (POC used 15).

## Enrichment (LLM)
- Provider is HIDDEN behind an interface: enrich(cluster) -> {title, bullets}.
  Which provider/model is an implementation detail, swappable without touching
  the rest of presentation.
- Provider/model config lives in presentation/config.py (local, like grouping's
  thresholds). API key lives in .env (secret, read from environment).
- Provider choice (OpenAI vs Gemini) is PARKED — decide when building
  enrichment, with a current cost/quality check.
- v1: NO cache. Enrichment recomputed each run. Known accepted tradeoff: titles/
  bullets may change between runs. Stable story identity + caching is a separate
  parked high-priority task.
- Enrichment input: POC fed titles only. Whether to also feed perex/summary is
  parked (quality vs cost).

## Contract output persistence (db)
Story cards are pipeline data (web reads them) -> a new db table, written via a
repository function, full-replace each run (same pattern as article_clusters).
Exact shape (one table vs cards + sources) to confirm when scoping db work.

## Carry vs leave (from POC)
Carry:
- ClusterRanker (aggregate, filter >=2 media, rank_score, sort)
- ClusterEnricher (LLM title + bullets), provider behind interface
- TF-IDF keywords (moved here from grouping) — as fallback title when LLM
  missing / cluster not in top N
Leave / change:
- cache-by-cluster_id logic — DROPPED for v1 (no cache; parked with stable
  identity)
- CSV persistence -> db
- top-15 cap belongs here (ranking), not in web (web is dumb render)

## Parked (do NOT implement / decide now)
- enrichment cache + stable story identity (separate high-priority task)
- LLM provider choice (decide when building enrichment)
- enrichment input fields (titles only vs + perex)
- near-identical/syndication dedup (belongs near grouping)

## Open questions (for later)
- top N value (POC 15) — confirm or make configurable
- fallback when LLM fails (keywords? raw title?)

---

# Claude's review (2026-07-16)

Overall: the sharpest plan yet. It correctly nails the granularity change
(per-article -> per-cluster), the >=2 media filter (which elegantly disposes of
the singletons grouping produced — they never reach the page), provider-behind-
interface, no-cache-for-v1, db persistence, and a clean carry-vs-leave. Feedback
below is about decisions still open that block or shape the build. Answer inline
(`A:` lines). No code until resolved.

## Questions I need you to answer

### Q1 — LLM provider (blocks building enrichment)
The plan parks the provider "until we build enrichment" — that's now. Two paths:
  (a) Build presentation WITHOUT the LLM first (ranking + card assembly +
      keyword-title fallback), verify end-to-end producing real cards, then slot
      in the concrete provider behind the interface once chosen — my strong
      recommendation (unblocks ~80% now, keeps provider deferred but isolated).
  (b) Pick the provider now: OpenAI (POC used gpt-4o-mini) / Gemini / Claude
      (e.g. Haiku, worth considering for cost/quality).
A: (a) — build presentation WITHOUT the LLM first: ranking + card assembly +
keyword-title fallback, verified end-to-end producing real cards. Slot in the
concrete provider behind the enrich() interface later, once chosen. Provider
stays parked and isolated; this unblocks the rest now.

### Q2 — story-card db shape
  (a) ONE denormalized `story_cards` table, JSONB for list fields (sources,
      bullets), full-replace each run — my lean; matches "ready to render",
      keeps web dumb.
  (b) Two tables (`story_cards` + `story_card_sources`) — more relational, but
      forces web to join.
A: (a) — ONE denormalized story_cards table, JSONB for list fields (sources,
bullets), full-replace each run (same pattern as article_clusters). DB (not a
JSON file) because Heroku's ephemeral filesystem rules out file storage, and to
stay consistent with the rest of the pipeline (everything else is in DB). JSONB
here is a column type inside the table, not a separate file.

### Q3 — which clusters become cards
  (a) Write ONLY top N cards (all LLM-enriched; keyword fallback only if LLM
      fails). Simpler.
  (b) Write ALL >=2-media clusters as cards, but LLM-enrich only the top N; the
      rest get keyword titles. More stories on the page, LLM cost still capped.
The plan is ambiguous (says "enrich top N" but also "keywords as fallback when
cluster not in top N"). This changes the output contract — pick one.
A: (a) — write ONLY top N cards. Clean "top stories" page, no long tail. N is
arbitrary for now (see Q7), may increase later.

### Q4 — self-contained cards (web does no joins)
The POC web re-joins articles per cluster to build the source list + pick the
image. Our architecture says web = dumb render. So presentation should bake
sources, image_url, and counts INTO the card at build time; web reads ONLY
`story_cards`, no joins. (Gently overrides the CLAUDE.md "downstream joins back
via article_id" note for the web layer.) Confirm this is the intent.
A: Confirmed. Cards are self-contained — presentation bakes sources, image_url,
and counts INTO the card at build time. Web reads ONLY story_cards, no joins.
Web stays a dumb render layer. (This intentionally overrides the general
"downstream joins via article_id" note for the web layer specifically.)

### Q5 — keywords computation relocates to presentation
We stripped TF-IDF from grouping, so presentation computes keywords itself
(carry the POC's `_extract_cluster_keywords` + `SK_STOP_WORDS`). Confirm.
A: Confirmed. Keywords are computed in presentation (carry the POC's
_extract_cluster_keywords + SK_STOP_WORDS). They serve as the fallback title
when the LLM is missing/fails.

### Q6 — LLM-failure fallback
Recommend: keyword title + empty bullets, so a card still renders. Confirm.
A: Confirmed. On LLM failure: keyword title + empty bullets, so the card still
renders. (For v1 there's no LLM yet, so all cards use the keyword title by
default — the fallback path IS the v1 path until the provider is added.)

### Q7 — top N value
Keep 15 (POC), placed in `presentation/config.py` so it's tunable. Confirm.
A: Keep N=15 (arbitrary, for testing), placed in presentation/config.py so it's
tunable. Likely raised later.

## POC note
`run_post_clustering.py` has cache-by-cluster_id logic (preserving old
enrichments across runs). That is the piece to DROP for v1, exactly as the plan
says (no cache; parked with stable identity).