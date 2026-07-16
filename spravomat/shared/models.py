# spravomat/shared/models.py

"""
Shared data contracts that flow between components.

`Article` is the unified schema produced by `acquisition` and persisted by `db`.
It lives in `shared` so neither component imports the other's internals
(Low Coupling): acquisition builds it, db stores it.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    """
    A normalized news article, ready to be stored in the articles table.

    Holds only the insertable fields. `article_id` (auto-increment primary key)
    and `fetched_at` (DB default now()) are assigned by the database, so they
    are intentionally absent here.

    Attributes:
        title: Article headline.
        url: Canonical article URL. Unique — used as the deduplication key.
        medium: Canonical outlet key (e.g. "sme"). Must be consistent across
            RSS and perex so the two can be joined.
        category: Section/category label, or None if the source does not
            provide one.
        published_at: When the article was published (the source's timestamp).
        summary: Short summary from the RSS feed, or None.
        perex: Lead paragraph scraped from the article page. Best-effort, so it
            may be None (unsupported medium or failed scrape).
        image_url: Lead image URL, or None if absent / not extracted.
        attributes: Free JSONB bag for optional/future fields (author, tags,
            ...). Empty dict by default.
    """

    title: str
    url: str
    medium: str
    category: str | None
    published_at: datetime
    summary: str | None
    perex: str | None
    image_url: str | None
    attributes: dict = field(default_factory=dict)


@dataclass
class StoredArticle:
    """
    A news article as read back from the database — a full row.

    The read counterpart of `Article`: it includes the database-assigned fields
    (`article_id`, `fetched_at`) that `Article` omits. Returned by db read
    functions and consumed by downstream components (grouping, presentation).

    Attributes:
        article_id: Database primary key; the join key across the pipeline.
        title: Article headline.
        url: Canonical article URL (unique).
        medium: Canonical outlet key (e.g. "sme").
        category: Section/category label, or None.
        published_at: When the article was published (source's time), or None.
        fetched_at: When the row was stored (database clock).
        summary: Short summary from the RSS feed, or None.
        perex: Scraped lead paragraph, or None.
        image_url: Lead image URL, or None.
        attributes: Free JSONB bag for optional/future fields.
    """

    article_id: int
    title: str
    url: str
    medium: str
    category: str | None
    published_at: datetime | None
    fetched_at: datetime
    summary: str | None
    perex: str | None
    image_url: str | None
    attributes: dict = field(default_factory=dict)
