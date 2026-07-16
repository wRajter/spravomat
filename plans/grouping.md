# Plan — grouping

## Purpose
Turn articles into stories. Takes articles from db, groups the ones about the
same event into clusters, and outputs which article belongs to which cluster.
The "heart" of the product (lateral reading = same event across many outlets).

## Contract
- Input: articles from db (the source of truth).
- Output: POOR contract — `article_id -> cluster_id`, only for articles that
  passed. Uncategorized articles are not passed on. Confidence score stays
  internal.
- Private state: embeddings / model — hidden inside grouping, NOT part of the
  contract, may not be SQL.
- Fully hidden: embedding model, clustering algorithm, thresholds, similarity,
  scoring rules. Changing any of these must not affect downstream.

## Scope for v1 — BATCH ONLY
- Build only the batch regime: rebuild all clusters from scratch each run.
- Online (incremental) regime is PARKED — added later only if measurement shows
  batch is too expensive to run often. The stable contract lets us add it later
  without touching downstream.
- This is the KISS choice: online existed in the POC only because batch was
  expensive; the N³ bug fix may remove that reason.

## What the batch regime does (from POC, as reference)
- Embed articles (bge-m3), compute similarity, agglomerative clustering,
  score each article (confidence), drop uncategorized (below threshold).
- The N³ bug fix (memoized threshold clustering) is already done in the POC —
  carry that improvement over, do not reintroduce the bug.

## Parked (do NOT implement / decide now)
- batch vs online (waits on measurement)
- how/where the internal state persists (tied to batch/online decision)
- clustering algorithm changes, blocking, dedup of near-identical articles
- these are internal to grouping — safe to decide later behind the contract.

## Open questions (for later, with real data)
- Measure clustering on real data (the parked measurement): performance +
  fragmentation, using the notebook 03 harness. Decides algorithm/regime.
- Threshold/linkage re-validation against ground truth at production settings.

## Reference (POC — spravomat-poc repo)
- clustering/clusterer.py — batch + online + scoring
- notebooks/ — ground-truth harness (ARI/NMI), threshold tuning

---

# Claude's review (2026-07-16)

Overall: solid and well-aligned with the architecture — batch-only, poor
contract, private embeddings, KISS. The scoping instinct (park online,
persistence-of-state, algorithm tuning) is right. The feedback below is mostly
gaps that will bite downstream if not pinned now, not disagreements. Answer
inline under each question (`A:` lines). No code until resolved.

## Gaps in the plan (my findings)

1. **The contract output has no defined home.** Output is `article_id ->
   cluster_id`, but the plan never says where it is persisted. That mapping is
   PIPELINE DATA (presentation + web must read it), so it needs a home in `db`
   (e.g. an `article_clusters` table via a repository function), like
   `articles`. This is separate from grouping's INTERNAL state (embeddings/model),
   which stays hidden and may be non-SQL. Rule to state explicitly: contract
   output -> db; internal state -> hidden inside grouping.

2. **`cluster_id` is ephemeral across runs.** Batch rebuilds every cluster from
   scratch, so `cluster_id=5` today is a different story than `cluster_id=5`
   tomorrow — IDs do not persist across runs. The POC even deletes
   `ranked_clusters.csv` each batch run for this reason ("enrichments would have
   invalid cluster IDs"). Consequence: downstream must treat each batch as a
   FULL REPLACEMENT SNAPSHOT, not stable story identities. Directly ties into
   the parked "enrichment cache strategy".

3. **Input scope is undefined.** "Input: articles from db" — but which? All
   articles, or a rolling window (e.g. last 7 days)? The set determines cost and
   which stories can form. Retention is orchestration's job, but grouping needs
   a stated input contract.

## POC assessment (what to carry vs leave)

The POC `clustering/` folder MIXES grouping and presentation concerns. For the
grouping component, carry only:
- embed -> cosine similarity -> agglomerative clustering (complete linkage,
  precomputed distance)
- the memoized threshold scoring + uncategorized drop (this IS the N³ fix —
  `threshold_labels` computed once, not per-article; carry it)

Leave out / move elsewhere:
- online_clustering — parked (plan already says so)
- TF-IDF keywords — descriptive enrichment -> presentation, not needed for the
  `article_id -> cluster_id` contract
- cluster_ranking.py, llm_enrichment.py — presentation
- pickle save/load + save_csv in that shape — persistence parked; contract
  output goes to db

Net: grouping should be noticeably leaner than the POC's ~420-line clusterer.
Do NOT port the class wholesale.

## Questions I need you to answer

### Q1 — contract output persistence
Persist `article_id -> cluster_id` in a new `db` table (my proposal:
`article_clusters(article_id, cluster_id, batch_id/created_at)`), written via a
db repository function, replacing the previous batch's rows each run? Confirm,
or propose another home.
A:Confirmed. New db table article_clusters(article_id, cluster_id, +
created_at/batch_id), written via a db repository function, replacing the
previous batch's rows each run. This is pipeline data (presentation reads it),
so it belongs in db — separate from grouping's internal state (embeddings),
which stays hidden and may be non-SQL.

### Q2 — cluster_id ephemerality
Confirm the contract states cluster_ids are per-batch (not stable across runs),
so downstream consumes a whole batch snapshot. If we later need stable story
identities (for enrichment caching), that's a separate parked decision — ok?
A: Confirmed. cluster_ids are per-batch, NOT stable across runs. Downstream
consumes each batch as a full-replacement snapshot. Stable story identity (for
enrichment caching) is a SEPARATE PARKED TASK — high priority, to be designed in
isolation later, after grouping and presentation exist. Do not solve it here.

### Q3 — input scope
What set does batch cluster over? Options: (a) all articles currently in db
(retention already bounds this upstream) — my lean; (b) an explicit rolling
window inside grouping (e.g. last 7 days). Which?
A: (a) — cluster over all articles currently in db. Retention bounds this
upstream (deleting old rows is an orchestration step). Grouping must NOT know
about retention or filter by freshness itself — it takes the whole db content.

### Q4 — embedding input fields
POC embeds `title + summary + perex` truncated to 500 chars. Given perex is
often empty/redundant, use `title + summary` (+ perex when present)? Confirm the
field choice and whether to keep the 500-char truncation.
A: Embed title (always) + summary (when present) + perex (when present),
concatenated into one text. The 500-char limit is on the CONCATENATED text as a
whole (not per field) — same as POC. Order: title → summary → perex, so long
text truncates from the end (perex yields first). That's fine: title/summary
matter most for topic detection.
The summary/perex redundancy is a KNOWN, ACCEPTED tradeoff for v1 — do NOT try
to optimize it away (no dedup/similarity checks between fields). If it ever
proves to hurt clustering, that's addressed later with the parked measurement,
with real data. Keep POC behavior for now.

### Q5 — carry-vs-leave split
Confirm the split above: grouping keeps only clustering + scoring + uncategorized
drop; keywords/ranking/enrichment go to presentation; online + pickle dropped
for now.
A: Confirmed. Grouping keeps ONLY: embed → similarity → agglomerative clustering
→ scoring → drop uncategorized. Keywords (TF-IDF), ranking, LLM enrichment →
presentation. online + pickle persistence dropped for now. Grouping should be
noticeably leaner than the POC's ~420-line clusterer — do not port the class
wholesale.

### Q6 — thresholds
Carry the POC values as-is for v1 (BASE_THRESHOLD=0.40, THRESHOLDS=[0.3, 0.35,
0.4, 0.45, 0.5], UNCATEGORIZED_THRESHOLD=5, complete linkage)? Re-validation
against ground truth is already an open question for later.
A: Carry POC values as-is for v1 (BASE_THRESHOLD=0.40, THRESHOLDS=[0.3,0.35,0.4,
0.45,0.5], UNCATEGORIZED_THRESHOLD=5, complete linkage). Reason: we have no real
data to re-validate against yet — that's the parked measurement. Using proven
POC values is the only grounded choice; changing them blind would have nothing
to stand on. Re-validation stays an open question for later.