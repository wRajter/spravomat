# spravomat/db/repository.py

"""
Repository — the only way in and out of the database.

Every function returns the standard dict {"success", "message", "data"}, wraps
SQL in try/except, and logs failures. Callers never see SQL or psycopg.
"""

import logging

from psycopg.types.json import Jsonb

from spravomat.db.connection import connection
from spravomat.shared.models import Article

logger = logging.getLogger(__name__)


def get_existing_urls(urls: list[str]) -> dict:
    """
    Return which of the given URLs are already stored.

    Used by acquisition's dedup phase to avoid re-scraping perex for articles we
    already have.

    Args:
        urls: Candidate article URLs.

    Returns:
        Standard dict; data is a set[str] of URLs that already exist. Empty set
        (no query) if `urls` is empty.
    """
    if not urls:
        return {"success": True, "message": "No URLs to check", "data": set()}

    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT url FROM articles WHERE url = ANY(%s)",
                    (urls,),
                )
                existing = {row[0] for row in cur.fetchall()}
        return {
            "success": True,
            "message": f"{len(existing)} of {len(urls)} URLs already exist",
            "data": existing,
        }
    except Exception as e:
        logger.error(f"❌ get_existing_urls failed: {e}")
        return {"success": False, "message": str(e), "data": None}


def save_articles(articles: list[Article]) -> dict:
    """
    Insert articles, skipping any whose URL already exists.

    Uses ON CONFLICT (url) DO NOTHING as a safety net against concurrent runs.
    `article_id` and `fetched_at` are assigned by the database; `attributes` is
    stored as JSONB.

    Args:
        articles: Normalized articles to store.

    Returns:
        Standard dict; data is the number of rows actually inserted.
    """
    if not articles:
        return {"success": True, "message": "No articles to save", "data": 0}

    rows = [
        (
            a.title,
            a.url,
            a.medium,
            a.category,
            a.published_at,
            a.summary,
            a.perex,
            a.image_url,
            Jsonb(a.attributes),
        )
        for a in articles
    ]

    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO articles
                        (title, url, medium, category, published_at,
                         summary, perex, image_url, attributes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING
                    """,
                    rows,
                )
                inserted = cur.rowcount
        message = f"Inserted {inserted} of {len(articles)} articles ({len(articles) - inserted} already existed)"
        logger.info(f"🏁 {message}")
        return {"success": True, "message": message, "data": inserted}
    except Exception as e:
        logger.error(f"❌ save_articles failed: {e}")
        return {"success": False, "message": str(e), "data": None}
