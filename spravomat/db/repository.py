# spravomat/db/repository.py

"""
Repository — the only way in and out of the database.

Every function returns the standard dict {"success", "message", "data"}, wraps
SQL in try/except, and logs failures. Callers never see SQL or psycopg.
"""

import logging

from psycopg.types.json import Jsonb

from spravomat.db.connection import connection
from spravomat.shared.models import Article, StoredArticle, StoryCard

logger = logging.getLogger(__name__)

# Column order for reading full article rows into StoredArticle.
_ARTICLE_COLUMNS = (
    "article_id, title, url, medium, category, published_at, "
    "fetched_at, summary, perex, image_url, attributes"
)


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


def get_all_articles() -> dict:
    """
    Read every stored article as a full row.

    Used by grouping, which clusters over all articles currently in the database
    (retention bounds the set upstream).

    Returns:
        Standard dict; data is a list[StoredArticle].
    """
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT {_ARTICLE_COLUMNS} FROM articles")
                articles = [StoredArticle(*row) for row in cur.fetchall()]
        return {
            "success": True,
            "message": f"Read {len(articles)} articles",
            "data": articles,
        }
    except Exception as e:
        logger.error(f"❌ get_all_articles failed: {e}")
        return {"success": False, "message": str(e), "data": None}


def replace_clusters(mapping: dict[int, int]) -> dict:
    """
    Replace the entire article -> cluster mapping with a new batch.

    Clears the previous batch and inserts the new one in a single transaction,
    so the snapshot is atomic (whole replacement or nothing).

    Args:
        mapping: {article_id: cluster_id} for articles that passed clustering.

    Returns:
        Standard dict; data is the number of mapping rows written.
    """
    rows = list(mapping.items())
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM article_clusters")
                if rows:
                    cur.executemany(
                        "INSERT INTO article_clusters (article_id, cluster_id) VALUES (%s, %s)",
                        rows,
                    )
        message = f"Replaced cluster mapping with {len(rows)} rows"
        logger.info(f"🏁 {message}")
        return {"success": True, "message": message, "data": len(rows)}
    except Exception as e:
        logger.error(f"❌ replace_clusters failed: {e}")
        return {"success": False, "message": str(e), "data": None}


def get_cluster_mapping() -> dict:
    """
    Read the current article -> cluster mapping.

    Used by presentation to aggregate articles into clusters.

    Returns:
        Standard dict; data is {article_id: cluster_id}.
    """
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT article_id, cluster_id FROM article_clusters")
                mapping = {row[0]: row[1] for row in cur.fetchall()}
        return {
            "success": True,
            "message": f"Read {len(mapping)} cluster assignments",
            "data": mapping,
        }
    except Exception as e:
        logger.error(f"❌ get_cluster_mapping failed: {e}")
        return {"success": False, "message": str(e), "data": None}


def replace_story_cards(cards: list[StoryCard]) -> dict:
    """
    Replace the entire set of story cards with a new run.

    Clears the previous run's cards and inserts the new ones in a single
    transaction, so the snapshot is atomic (whole replacement or nothing).

    Args:
        cards: The finished, display-ready story cards to store.

    Returns:
        Standard dict; data is the number of cards written.
    """
    rows = [
        (
            c.cluster_id,
            c.title,
            Jsonb(c.bullets),
            Jsonb(c.sources),
            c.image_url,
            c.media_count,
            c.article_count,
            c.newest_at,
            c.rank_score,
        )
        for c in cards
    ]
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM story_cards")
                if rows:
                    cur.executemany(
                        """
                        INSERT INTO story_cards
                            (cluster_id, title, bullets, sources, image_url,
                             media_count, article_count, newest_at, rank_score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        rows,
                    )
        message = f"Replaced story cards with {len(rows)} cards"
        logger.info(f"🏁 {message}")
        return {"success": True, "message": message, "data": len(rows)}
    except Exception as e:
        logger.error(f"❌ replace_story_cards failed: {e}")
        return {"success": False, "message": str(e), "data": None}


def delete_articles_older_than(days: int) -> dict:
    """
    Delete articles whose `fetched_at` is older than `days` days.

    Used by the retention step. `article_clusters` rows are removed automatically
    via ON DELETE CASCADE. Retention is keyed on `fetched_at` (NOT NULL) so every
    article ages out cleanly, regardless of the nullable `published_at`.

    Args:
        days: Maximum age in days; older articles are deleted.

    Returns:
        Standard dict; data is the number of articles deleted.
    """
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM articles WHERE fetched_at < now() - make_interval(days => %s)",
                    (days,),
                )
                deleted = cur.rowcount
        message = f"Deleted {deleted} articles older than {days} days"
        logger.info(f"🏁 {message}")
        return {"success": True, "message": message, "data": deleted}
    except Exception as e:
        logger.error(f"❌ delete_articles_older_than failed: {e}")
        return {"success": False, "message": str(e), "data": None}


def get_story_cards() -> dict:
    """
    Read all story cards, highest-ranked first.

    Used by the web layer to render the page. Cards are self-contained, so no
    joins are needed. JSONB `bullets`/`sources` come back as Python list/dict.

    Returns:
        Standard dict; data is a list[StoryCard] ordered by rank_score desc.
    """
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT cluster_id, title, bullets, sources, image_url,
                           media_count, article_count, newest_at, rank_score
                    FROM story_cards
                    ORDER BY rank_score DESC
                    """
                )
                cards = [StoryCard(*row) for row in cur.fetchall()]
        return {
            "success": True,
            "message": f"Read {len(cards)} story cards",
            "data": cards,
        }
    except Exception as e:
        logger.error(f"❌ get_story_cards failed: {e}")
        return {"success": False, "message": str(e), "data": None}
