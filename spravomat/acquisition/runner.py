# spravomat/acquisition/runner.py

"""
Acquisition runner — the component's public entry point.

Coordinates the four phases in order:

    fetch (RSS) -> dedup -> enrich (perex) -> store

Dedup runs before enrich so perex is scraped only for genuinely new articles.
Phases are fail-fast: if one fails, the run stops and reports which phase failed.
"""

import logging
import time

from spravomat.acquisition.perex import PEREX_RATE_LIMIT_SECONDS, PerexScraper
from spravomat.acquisition.rss import RSSFetcher
from spravomat.acquisition.sources import SOURCE_SPECS, SourceSpec
from spravomat.db import repository
from spravomat.shared.models import Article

logger = logging.getLogger(__name__)


def run(specs: list[SourceSpec] | None = None) -> dict:
    """
    Run the acquisition pipeline: fetch, dedup, enrich, store.

    Args:
        specs: Sources to fetch. Defaults to all configured sources; override
            (e.g. a single source) for testing.

    Returns:
        Standard dict; data holds counts
        {"fetched", "new", "enriched", "inserted"}.
    """
    if specs is None:
        specs = SOURCE_SPECS

    logger.info("🚀 Acquisition started")

    # 1. Fetch
    fetch_result = RSSFetcher().fetch_all(specs)
    if not fetch_result["success"]:
        return _failed("fetch", fetch_result["message"])
    articles = fetch_result["data"]

    # 2. Dedup — keep only articles whose URL is not already stored
    existing_result = repository.get_existing_urls([a.url for a in articles])
    if not existing_result["success"]:
        return _failed("dedup", existing_result["message"])
    existing_urls = existing_result["data"]
    new_articles = [a for a in articles if a.url not in existing_urls]
    logger.info(f"ℹ️ Dedup: {len(new_articles)} new of {len(articles)} fetched")

    # 3. Enrich — scrape perex for new articles only (best-effort)
    enriched = _enrich(new_articles)

    # 4. Store
    save_result = repository.save_articles(new_articles)
    if not save_result["success"]:
        return _failed("store", save_result["message"])
    inserted = save_result["data"]

    counts = {
        "fetched": len(articles),
        "new": len(new_articles),
        "enriched": enriched,
        "inserted": inserted,
    }
    logger.info(f"🏁 Acquisition done: {counts}")
    return {"success": True, "message": "Acquisition completed", "data": counts}


def _enrich(articles: list[Article]) -> int:
    """
    Scrape perex for each supported article (best-effort), setting article.perex.

    Applies a politeness delay between requests. Returns the number of articles
    for which a perex was obtained.
    """
    scraper = PerexScraper()
    enriched = 0
    for article in articles:
        if not scraper.is_supported(article.url):
            continue
        perex = scraper.get_perex(article.url)
        if perex:
            article.perex = perex
            enriched += 1
        time.sleep(PEREX_RATE_LIMIT_SECONDS)
    logger.info(f"ℹ️ Enrich: perex obtained for {enriched} of {len(articles)} new articles")
    return enriched


def _failed(phase: str, message: str) -> dict:
    """Build a standard failure dict for a failed phase (fail-fast)."""
    full = f"Acquisition failed at {phase}: {message}"
    logger.error(f"❌ {full}")
    return {"success": False, "message": full, "data": None}
