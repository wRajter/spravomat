# spravomat/presentation/ranking.py

"""
Cluster aggregation and ranking.

`Cluster` is presentation's internal view of a story: the articles that share a
cluster_id, plus derived aggregates. `ClusterRanker` groups articles by cluster,
keeps only lateral-reading stories (>= MIN_MEDIA media), scores them, and sorts.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from spravomat.presentation import config
from spravomat.shared.models import StoredArticle

logger = logging.getLogger(__name__)


@dataclass
class Cluster:
    """
    A cluster of articles about the same event, with derived aggregates.

    Internal to presentation (not a cross-component contract). Counts are derived
    from `articles` so they can never drift out of sync.

    Attributes:
        cluster_id: The (ephemeral, per-batch) cluster id.
        articles: The articles belonging to this cluster.
        rank_score: Ranking score, set by ClusterRanker (0 until scored).
    """

    cluster_id: int
    articles: list[StoredArticle]
    rank_score: int = 0

    @property
    def article_count(self) -> int:
        """Number of articles in the cluster."""
        return len(self.articles)

    @property
    def media_count(self) -> int:
        """Number of distinct outlets covering the story."""
        return len({article.medium for article in self.articles})

    @property
    def newest_at(self) -> datetime | None:
        """Publication time of the newest article, or None if none have a date."""
        times = [a.published_at for a in self.articles if a.published_at]
        return max(times) if times else None


class ClusterRanker:
    """Aggregates articles into clusters, filters to lateral stories, and ranks them."""

    def rank(self, mapping: dict[int, int], articles: list[StoredArticle]) -> list[Cluster]:
        """
        Group articles by cluster, keep >= MIN_MEDIA-media clusters, score, sort.

        Args:
            mapping: {article_id: cluster_id} from grouping.
            articles: All stored articles (joined in memory by article_id).

        Returns:
            Clusters sorted by rank_score, highest first.
        """
        clusters = self._aggregate(mapping, articles)
        lateral = [c for c in clusters if c.media_count >= config.MIN_MEDIA]
        for cluster in lateral:
            cluster.rank_score = self._score(cluster)
        lateral.sort(key=lambda c: c.rank_score, reverse=True)
        logger.info(
            f"ℹ️ Ranked {len(lateral)} lateral clusters "
            f"(>= {config.MIN_MEDIA} media) of {len(clusters)} total"
        )
        return lateral

    def _aggregate(self, mapping: dict[int, int], articles: list[StoredArticle]) -> list[Cluster]:
        """Group articles by their cluster_id using the mapping."""
        by_id = {a.article_id: a for a in articles}
        grouped: dict[int, list[StoredArticle]] = {}
        for article_id, cluster_id in mapping.items():
            article = by_id.get(article_id)
            if article is not None:
                grouped.setdefault(cluster_id, []).append(article)
        return [Cluster(cluster_id=cid, articles=arts) for cid, arts in grouped.items()]

    def _score(self, cluster: Cluster) -> int:
        """rank_score = size + media + freshness (POC weights)."""
        size_score = min(cluster.article_count, 10)
        media_score = cluster.media_count * 3
        return size_score + media_score + self._freshness_score(cluster.newest_at)

    def _freshness_score(self, newest_at: datetime | None) -> int:
        """Recency of the newest article: <6h -> 5, <24h -> 3, <48h -> 1, else 0."""
        if newest_at is None:
            return 0
        hours = (datetime.now(timezone.utc) - newest_at).total_seconds() / 3600
        if hours < 6:
            return 5
        if hours < 24:
            return 3
        if hours < 48:
            return 1
        return 0
