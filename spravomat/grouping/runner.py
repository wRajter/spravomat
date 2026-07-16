# spravomat/grouping/runner.py

"""
Grouping runner — the component's public entry point.

Batch regime: read all articles from db, cluster them from scratch, and write
the article -> cluster mapping back to db (full replacement). Fail-fast between
phases.
"""

import logging

from spravomat.db import repository
from spravomat.grouping.clusterer import Clusterer

logger = logging.getLogger(__name__)


def run() -> dict:
    """
    Run batch grouping: read -> cluster -> write mapping.

    Returns:
        Standard dict; data holds counts
        {"articles", "categorized", "dropped", "clusters"}.
    """
    logger.info("🚀 Grouping started")

    # 1. Read all articles currently in the database.
    read_result = repository.get_all_articles()
    if not read_result["success"]:
        return _failed("read", read_result["message"])
    articles = read_result["data"]

    # 2. Cluster (rebuilds all clusters from scratch).
    mapping = Clusterer().cluster(articles)

    # 3. Write the mapping, replacing the previous batch.
    write_result = repository.replace_clusters(mapping)
    if not write_result["success"]:
        return _failed("write", write_result["message"])

    counts = {
        "articles": len(articles),
        "categorized": len(mapping),
        "dropped": len(articles) - len(mapping),
        "clusters": len(set(mapping.values())),
    }
    logger.info(f"🏁 Grouping done: {counts}")
    return {"success": True, "message": "Grouping completed", "data": counts}


def _failed(phase: str, message: str) -> dict:
    """Build a standard failure dict for a failed phase (fail-fast)."""
    full = f"Grouping failed at {phase}: {message}"
    logger.error(f"❌ {full}")
    return {"success": False, "message": full, "data": None}
