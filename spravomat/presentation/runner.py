# spravomat/presentation/runner.py

"""
Presentation runner — the component's public entry point.

Reads the cluster mapping + articles, ranks the clusters, takes the top N, builds
self-contained story cards, and writes them to db (full replacement). Fail-fast
between phases.
"""

import logging

from spravomat.db import repository
from spravomat.presentation import config
from spravomat.presentation.cards import build_cards
from spravomat.presentation.enrichment import KeywordEnricher
from spravomat.presentation.ranking import ClusterRanker

logger = logging.getLogger(__name__)


def run() -> dict:
    """
    Run presentation: read -> rank -> top N -> build cards -> write.

    Returns:
        Standard dict; data holds counts {"lateral_clusters", "cards"}.
    """
    logger.info("🚀 Presentation started")

    # 1. Read the cluster mapping and the articles.
    mapping_result = repository.get_cluster_mapping()
    if not mapping_result["success"]:
        return _failed("read mapping", mapping_result["message"])
    articles_result = repository.get_all_articles()
    if not articles_result["success"]:
        return _failed("read articles", articles_result["message"])

    # 2. Rank clusters, take the top N.
    ranked = ClusterRanker().rank(mapping_result["data"], articles_result["data"])
    top = ranked[: config.TOP_N]

    # 3. Build self-contained cards (keyword titles in v1; LLM later).
    cards = build_cards(top, KeywordEnricher())

    # 4. Write, replacing the previous run's cards.
    write_result = repository.replace_story_cards(cards)
    if not write_result["success"]:
        return _failed("write", write_result["message"])

    counts = {"lateral_clusters": len(ranked), "cards": len(cards)}
    logger.info(f"🏁 Presentation done: {counts}")
    return {"success": True, "message": "Presentation completed", "data": counts}


def _failed(phase: str, message: str) -> dict:
    """Build a standard failure dict for a failed phase (fail-fast)."""
    full = f"Presentation failed at {phase}: {message}"
    logger.error(f"❌ {full}")
    return {"success": False, "message": full, "data": None}
