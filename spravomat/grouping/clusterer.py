# spravomat/grouping/clusterer.py

"""
The clustering engine.

`Clusterer` is a stateful object that, given a batch of articles, runs the full
batch pipeline — embed -> cosine similarity -> agglomerative clustering -> score
-> drop uncategorized — and returns which article belongs to which cluster.

It knows nothing about the database: articles come in as `StoredArticle` objects
and the result is a plain `{article_id: cluster_id}` mapping. All clustering
internals (model, embeddings, similarity matrix, thresholds, scoring) are hidden
here and are not part of any contract.
"""

import logging

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

from spravomat.grouping import config
from spravomat.shared.models import StoredArticle

logger = logging.getLogger(__name__)

# Max length of the concatenated text fed to the embedding model.
MAX_EMBED_CHARS = 500


class Clusterer:
    """Groups articles about the same event into clusters (batch regime)."""

    def __init__(self, model_name: str = config.MODEL_NAME):
        """
        Args:
            model_name: Sentence-embedding model to load.
        """
        # Imported lazily (not at module top) so that importing grouping —
        # e.g. orchestration or the web app pulling in grouping.run — does NOT
        # drag torch/sentence-transformers into memory. It loads only when a
        # Clusterer is actually constructed. Keeps the core light (the VPS has
        # limited RAM; batch peaks near the box's ceiling).
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.articles: list[StoredArticle] = []
        self.embeddings: np.ndarray | None = None
        self.similarity_matrix: np.ndarray | None = None
        self.labels: np.ndarray | None = None

    def cluster(self, articles: list[StoredArticle]) -> dict[int, int]:
        """
        Cluster a batch of articles.

        Args:
            articles: All articles to cluster.

        Returns:
            {article_id: cluster_id} for articles that passed (survived the
            uncategorized drop). Empty if fewer than 2 articles are given.
            cluster_ids are meaningful only within this batch.
        """
        self.articles = articles
        if len(articles) < 2:
            logger.warning(f"⚠️ Need at least 2 articles to cluster, got {len(articles)}")
            return {}

        # 1. Embed (title + summary + perex, truncated).
        texts = [self._embed_text(a) for a in articles]
        self.embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False)

        # 2. Similarity matrix.
        self.similarity_matrix = cosine_similarity(self.embeddings)

        # 3. Primary clustering.
        self.labels = self._cluster_labels(config.BASE_THRESHOLD)

        # 4. Score each article and keep only the confident ones.
        # Cluster labels per threshold are computed ONCE here (not per article) —
        # this is the memoized fix for the original N³ cost.
        threshold_labels = {t: self._cluster_labels(t) for t in config.THRESHOLDS}

        mapping: dict[int, int] = {}
        for idx, article in enumerate(articles):
            if self._confidence(idx, threshold_labels) >= config.UNCATEGORIZED_THRESHOLD:
                mapping[article.article_id] = int(self.labels[idx])

        dropped = len(articles) - len(mapping)
        clusters = len(set(mapping.values()))
        logger.info(
            f"ℹ️ Clustered {len(articles)} articles -> {clusters} clusters, "
            f"{len(mapping)} categorized, {dropped} dropped"
        )
        return mapping

    # ==========================================================
    # Embedding
    # ==========================================================

    def _embed_text(self, article: StoredArticle) -> str:
        """Build the text to embed: title + summary + perex (when present), truncated."""
        parts = [article.title or ""]
        if article.summary:
            parts.append(article.summary)
        if article.perex:
            parts.append(article.perex)
        return " ".join(parts)[:MAX_EMBED_CHARS]

    # ==========================================================
    # Clustering
    # ==========================================================

    def _cluster_labels(self, threshold: float) -> np.ndarray:
        """Run agglomerative clustering at a distance threshold; return per-article labels."""
        distance_matrix = 1 - self.similarity_matrix
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=threshold,
            metric="precomputed",
            linkage=config.LINKAGE,
        )
        return clustering.fit_predict(distance_matrix)

    def _cluster_mates(self, idx: int, labels: np.ndarray) -> list[int]:
        """Return the indices of articles sharing article `idx`'s cluster under `labels`."""
        cluster_id = labels[idx]
        return [i for i in range(len(labels)) if labels[i] == cluster_id]

    # ==========================================================
    # Scoring (confidence = threshold + media + time, range 0–9)
    # ==========================================================

    def _confidence(self, idx: int, threshold_labels: dict[float, np.ndarray]) -> int:
        """Total confidence score for one article."""
        mates = self._cluster_mates(idx, self.labels)
        return (
            self._threshold_score(idx, mates, threshold_labels)
            + self._media_score(mates)
            + self._time_score(idx, mates)
        )

    def _threshold_score(self, idx: int, base_mates: list[int],
                         threshold_labels: dict[float, np.ndarray]) -> int:
        """
        Stability score (0–5): how many thresholds give the article the exact
        same set of cluster mates as the primary clustering. Stable membership
        across thresholds = a confident cluster.
        """
        base_set = set(base_mates)
        score = 0
        for threshold in config.THRESHOLDS:
            labels = threshold_labels[threshold]
            if base_set == set(self._cluster_mates(idx, labels)):
                score += 1
        return score

    def _media_score(self, mates: list[int]) -> int:
        """Media diversity score: >=3 distinct media -> 2, exactly 2 -> 1, else 0."""
        media = {self.articles[i].medium for i in mates}
        if len(media) >= 3:
            return 2
        if len(media) == 2:
            return 1
        return 0

    def _time_score(self, idx: int, mates: list[int]) -> int:
        """
        Time-proximity score: closeness to the newest article in the cluster.
        <=24h -> 2, <=48h -> 1, else 0. Zero for singletons or missing dates.
        """
        if len(mates) <= 1:
            return 0
        article_time = self.articles[idx].published_at
        if article_time is None:
            return 0

        newest = None
        for i in mates:
            other = self.articles[i].published_at
            if other is not None and (newest is None or other > newest):
                newest = other
        if newest is None:
            return 0

        diff_hours = abs((article_time - newest).total_seconds() / 3600)
        if diff_hours <= 24:
            return 2
        if diff_hours <= 48:
            return 1
        return 0
