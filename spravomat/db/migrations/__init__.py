# spravomat/db/migrations/__init__.py

"""
Schema definition and idempotent initialization.

For v1 the schema is a single table created with CREATE ... IF NOT EXISTS and
re-run on each release (Heroku `release` phase). No versioned migration history
yet — that is added later, when the first real schema change makes the
idempotent approach awkward.
"""

import logging

from spravomat.db.connection import connection

logger = logging.getLogger(__name__)

# The full schema. Idempotent: safe to run repeatedly.
SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS articles (
    article_id   BIGSERIAL PRIMARY KEY,
    title        TEXT        NOT NULL,
    url          TEXT        NOT NULL UNIQUE,
    medium       TEXT        NOT NULL,
    category     TEXT,
    published_at TIMESTAMPTZ,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    summary      TEXT,
    perex        TEXT,
    image_url    TEXT,
    attributes   JSONB       NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles (published_at);

CREATE TABLE IF NOT EXISTS article_clusters (
    article_id BIGINT      PRIMARY KEY REFERENCES articles(article_id) ON DELETE CASCADE,
    cluster_id INTEGER     NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_article_clusters_cluster ON article_clusters (cluster_id);

CREATE TABLE IF NOT EXISTS story_cards (
    cluster_id    INTEGER     PRIMARY KEY,
    title         TEXT        NOT NULL,
    bullets       JSONB       NOT NULL DEFAULT '[]'::jsonb,
    sources       JSONB       NOT NULL DEFAULT '[]'::jsonb,
    image_url     TEXT,
    media_count   INTEGER     NOT NULL,
    article_count INTEGER     NOT NULL,
    newest_at     TIMESTAMPTZ,
    rank_score    INTEGER     NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def init_schema() -> dict:
    """
    Create the schema idempotently.

    Returns:
        Standard dict; data is None (this is a side-effecting operation).
    """
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_DDL)
        logger.info("🏁 Schema initialized (articles table ready)")
        return {"success": True, "message": "Schema initialized", "data": None}
    except Exception as e:
        logger.error(f"❌ Schema init failed: {e}")
        return {"success": False, "message": str(e), "data": None}
