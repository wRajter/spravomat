# Spec — grouping (finalized)

> Authoritative spec to build against. Consolidates the decisions made in
> `grouping.md` (kept as reference + full Q&A rationale). Finalized 2026-07-16.

## Purpose
Turn articles into stories. Read all articles from `db`, group the ones about
the same event into clusters, and output which article belongs to which cluster.
The heart of the product: lateral reading = the same event seen across many
outlets.

## Scope for v1 — BATCH ONLY
Rebuild all clusters from scratch each run. Online/incremental clustering is
PARKED (added later only if measurement shows batch is too expensive). The
stable contract lets us add it later without touching downstream.

## Pipeline (what a batch run does)
```
read articles (db) -> embed -> similarity -> cluster -> score -> drop uncategorized -> write mapping (db)
```
1. **read** — load all articles currently in `db` (see Input below).
2. **embed** — encode each article's text with bge-m3 (see Embedding input).
3. **similarity** — cosine similarity matrix over the embeddings.
4. **cluster** — agglomerative clustering, complete linkage, precomputed
   distance (`1 - similarity`), at `BASE_THRESHOLD`.
5. **score** — per-article confidence = threshold + media + time score
   (POC scoring; the memoized-threshold N³ fix carried over).
6. **drop uncategorized** — articles with confidence below
   `UNCATEGORIZED_THRESHOLD` are dropped (not passed on).
7. **write** — persist the `article_id -> cluster_id` mapping to `db`,
   replacing the previous batch.

## Contract
- **Input**: all articles currently in `db`. Grouping does NOT filter by
  freshness or know about retention — retention is an upstream orchestration
  step that bounds the set. Grouping takes the whole db content.
- **Output (POOR contract)**: `article_id -> cluster_id`, only for articles that
  passed (survived the uncategorized drop). Persisted in `db` (table
  `article_clusters`). Confidence score stays internal — never exposed.
- **`cluster_id` is EPHEMERAL**: rebuilt from scratch each run, so `cluster_id=5`
  today is a different story than `cluster_id=5` tomorrow. Downstream must treat
  each batch as a FULL-REPLACEMENT SNAPSHOT, not a stable story identity. Stable
  story identity (needed for enrichment caching) is a SEPARATE PARKED task, to
  be designed later — not solved here.
- **Private state (hidden)**: embedding model, embeddings, similarity matrix,
  clustering algorithm, thresholds, linkage, scoring rules. Not part of the
  contract; may be non-SQL. Changing any of these must not affect downstream.

## Embedding input
- Text = `title` (always) + `summary` (when present) + `perex` (when present),
  concatenated in that order into one string.
- Truncate the CONCATENATED text to 500 chars (as POC). Because order is
  title → summary → perex, overflow truncates from the end (perex drops first) —
  title/summary matter most for topic detection.
- The summary/perex redundancy is a KNOWN, ACCEPTED tradeoff for v1. Do NOT add
  dedup/similarity checks between fields. If it ever proves to hurt clustering,
  it's addressed later via the parked measurement with real data.

## Scoring (internal, POC values carried as-is)
Per-article confidence = `threshold_score + media_score + time_score`:
- **threshold_score (0–5)**: cluster-membership stability across `THRESHOLDS`.
  Cluster labels are computed ONCE per threshold (memoized), not per article —
  this is the N³ fix; do not reintroduce the per-article recomputation.
- **media_score (0–2)**: distinct media in the cluster (>=3 -> 2, 2 -> 1, else 0).
- **time_score (0–2)**: closeness to the newest article in the cluster
  (<=24h -> 2, <=48h -> 1, else 0).
- Drop when confidence `< UNCATEGORIZED_THRESHOLD`.

Thresholds (v1, unchanged from POC — no real data to re-validate against yet):
```
BASE_THRESHOLD         = 0.40
THRESHOLDS             = [0.30, 0.35, 0.40, 0.45, 0.50]
UNCATEGORIZED_THRESHOLD = 5
linkage                = "complete"
metric                 = "precomputed" (distance = 1 - cosine similarity)
MODEL_NAME             = "BAAI/bge-m3"
```

## Carry vs leave (from the POC `clustering/` folder)
Carry into grouping:
- embed -> cosine similarity -> agglomerative clustering (complete linkage)
- memoized threshold scoring + media/time scoring + uncategorized drop

Leave out / move elsewhere:
- `online_clustering` — PARKED
- TF-IDF keywords — PRESENTATION (descriptive enrichment, not in the contract)
- `cluster_ranking.py`, `llm_enrichment.py` — PRESENTATION
- pickle `save`/`load`, `save_csv` — persistence parked; contract output -> db

Grouping should be noticeably leaner than the POC's ~420-line clusterer. Do NOT
port the class wholesale.

## Dependency on `db` (new work grouping requires)
Grouping introduces read-side and a new write target in `db`:
1. **Read**: a repository function returning all stored articles as full rows
   (including `article_id`, needed as the join/mapping key). This needs the
   first read-side model — a stored-article representation (the `db/models.py`
   stub reserved earlier).
2. **Write**: a new table `article_clusters(article_id, cluster_id,
   created_at)` (batch_id optional) + a repository function that full-replaces
   the previous batch's rows. Schema added to the idempotent migration DDL.
   `article_id` is a foreign key back to `articles`.

Grouping never touches SQL directly — only these repository functions.

## Parked (do NOT implement / decide now)
- batch vs online (waits on measurement)
- how/where internal state (embeddings) persists (tied to batch/online)
- clustering algorithm changes, blocking, near-identical dedup
- stable story identity across batches (separate high-priority parked task)

## Open questions (for later, with real data)
- Measure clustering on real data (performance + fragmentation) using the
  notebook 03 ground-truth harness (ARI/NMI). Decides algorithm/regime.
- Threshold/linkage re-validation against ground truth at production settings.
