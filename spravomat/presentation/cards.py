# spravomat/presentation/cards.py

"""
Story card assembly.

Turns ranked clusters into self-contained `StoryCard` objects: the enricher
supplies title + bullets, and everything else the page needs (sources, image,
counts) is baked in here so the web layer performs no joins.
"""

import logging
from datetime import datetime, timezone

from spravomat.presentation.enrichment import Enricher
from spravomat.presentation.ranking import Cluster
from spravomat.shared.models import StoryCard

logger = logging.getLogger(__name__)

# Sentinel for sorting: articles with no date sort last (treated as oldest).
_OLDEST = datetime.min.replace(tzinfo=timezone.utc)


def build_cards(clusters: list[Cluster], enricher: Enricher) -> list[StoryCard]:
    """Build a self-contained story card for each ranked cluster."""
    return [_build_card(cluster, enricher) for cluster in clusters]


def _build_card(cluster: Cluster, enricher: Enricher) -> StoryCard:
    """Assemble one story card from a cluster and its enrichment."""
    enrichment = enricher.enrich(cluster)
    articles = sorted(cluster.articles, key=lambda a: a.published_at or _OLDEST, reverse=True)

    sources = [{"medium": a.medium, "title": a.title, "url": a.url} for a in articles]
    image_url = next((a.image_url for a in articles if a.image_url), None)

    return StoryCard(
        cluster_id=cluster.cluster_id,
        title=enrichment["title"],
        bullets=enrichment["bullets"],
        sources=sources,
        image_url=image_url,
        media_count=cluster.media_count,
        article_count=cluster.article_count,
        newest_at=cluster.newest_at,
        rank_score=cluster.rank_score,
    )
