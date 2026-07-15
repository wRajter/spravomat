# spravomat/acquisition/rss.py

"""
Generic RSS fetching and normalization.

`RSSFetcher` runs one common loop over all sources: fetch each feed, extract the
fields shared by every source, then apply the per-source strategies declared in
the `SourceSpec` (image, category). Output is a list of normalized `Article`
objects. The per-source differences live only in `sources.py`; the logic that
interprets the strategies lives here.
"""

import html
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import feedparser
import requests

from spravomat.acquisition.sources import SourceSpec, FEED_USER_AGENT
from spravomat.shared.models import Article

logger = logging.getLogger(__name__)

# Timeout (seconds) for feeds fetched via requests (use_headers=True).
FEED_FETCH_TIMEOUT = 10


class RSSFetcher:
    """Fetches and normalizes articles from RSS sources into `Article` objects."""

    def fetch_all(self, specs: list[SourceSpec]) -> dict:
        """
        Fetch and normalize every source.

        Per-feed failures are logged and skipped so one broken feed does not
        abort the run. Only an unexpected top-level error yields success=False.

        Args:
            specs: The source specifications to fetch.

        Returns:
            Standard dict; `data` is a list[Article] on success, None on failure.
        """
        try:
            articles: list[Article] = []
            for spec in specs:
                articles.extend(self._fetch_source(spec))
            message = f"Fetched {len(articles)} articles from {len(specs)} sources"
            logger.info(f"🏁 {message}")
            return {"success": True, "message": message, "data": articles}
        except Exception as e:
            logger.error(f"❌ RSS fetch failed: {e}")
            return {"success": False, "message": str(e), "data": None}

    # ==========================================================
    # Per-source fetching
    # ==========================================================

    def _fetch_source(self, spec: SourceSpec) -> list[Article]:
        """Fetch all feeds of one source and return its normalized articles."""
        articles: list[Article] = []
        for feed_label, url in spec.feeds.items():
            feed = self._fetch_feed(url, spec.use_headers)
            if not feed or not feed.entries:
                self._log_empty_feed(spec, url)
                continue
            for entry in feed.entries:
                article = self._build_article(entry, spec, feed_label)
                if article:
                    articles.append(article)
        logger.info(f"ℹ️ {spec.medium}: {len(articles)} articles")
        return articles

    def _log_empty_feed(self, spec: SourceSpec, url: str) -> None:
        """Log an empty/failed feed — calmly for known-blocked sources, else a warning."""
        if spec.known_blocked:
            logger.info(f"ℹ️ {spec.medium}: no entries (known blocked source, skipping)")
        else:
            logger.warning(f"⚠️ {spec.medium}: empty feed {url}")

    def _fetch_feed(self, url: str, use_headers: bool):
        """
        Fetch and parse one RSS feed.

        Args:
            url: Feed URL.
            use_headers: If True, fetch via requests with a browser User-Agent
                (for feeds that block the default client).

        Returns:
            The parsed feedparser result, or None on failure.
        """
        try:
            if use_headers:
                headers = {"User-Agent": FEED_USER_AGENT}
                response = requests.get(url, headers=headers, timeout=FEED_FETCH_TIMEOUT)
                feed = feedparser.parse(response.content)
            else:
                feed = feedparser.parse(url)
            return feed
        except Exception as e:
            logger.error(f"❌ Failed to fetch feed {url}: {e}")
            return None

    def _build_article(self, entry, spec: SourceSpec, feed_label: str | None) -> Article | None:
        """
        Build one normalized Article from a feed entry.

        Returns None (and logs a warning) if the entry lacks the fields we need
        to identify and store it (url, title).
        """
        title = entry.get("title")
        url = entry.get("link")
        if not url or not title:
            logger.warning(f"⚠️ {spec.medium}: skipping entry missing url/title")
            return None

        summary = self._clean_html(entry.get("summary"))
        published_at = self._parse_published_at(entry)
        if published_at is None:
            logger.warning(f"⚠️ {spec.medium}: no published date for {url}")

        return Article(
            title=title,
            url=url,
            medium=spec.medium,
            category=self._extract_category(entry, spec.category_strategy, feed_label, url),
            published_at=published_at,
            summary=summary,
            perex=None,  # filled later in the enrich phase
            image_url=self._extract_image(entry, spec.image_strategy),
        )

    # ==========================================================
    # Common field extraction
    # ==========================================================

    def _parse_published_at(self, entry) -> datetime | None:
        """
        Parse the entry's published date into a UTC-aware datetime, or None.

        feedparser normalizes published_parsed to UTC, so we attach UTC tzinfo
        to produce an unambiguous instant for the TIMESTAMPTZ column.
        """
        published_parsed = entry.get("published_parsed")
        if published_parsed:
            return datetime(*published_parsed[:6], tzinfo=timezone.utc)
        return None

    def _clean_html(self, text: str | None) -> str | None:
        """
        Turn a raw RSS summary into clean plain text: strip HTML tags and promo
        text (e.g. Euractiv's "The post"), decode HTML entities (&#160;, &amp;),
        and collapse whitespace (including the non-breaking spaces entities leave).
        """
        if not text:
            return text
        clean = re.sub(r"<[^>]+>", "", text)
        clean = re.sub(r"The post\s*$", "", clean)
        clean = html.unescape(clean)
        clean = " ".join(clean.split())
        return clean.strip()

    # ==========================================================
    # Strategy dispatch (per-source differences)
    # ==========================================================

    def _extract_image(self, entry, strategy: str) -> str | None:
        """Extract the image URL according to the source's image strategy."""
        if strategy == "links_by_type":
            for link in entry.get("links", []):
                if link.get("type") in ("image/jpeg", "image/png"):
                    return link.get("href")
            return None
        if strategy == "image_url":
            return entry.get("image_url")
        if strategy == "thumbnail":
            return entry.get("thumbnail")
        if strategy == "media_content":
            media = entry.get("media_content")
            if media:
                return media[0].get("url")
            return None
        return None  # "none" or unknown

    def _extract_category(self, entry, strategy: str, feed_label: str | None, url: str) -> str | None:
        """Extract the category according to the source's category strategy."""
        if strategy == "from_feed_key":
            return feed_label
        if strategy == "from_tags":
            tags = entry.get("tags", [])
            return tags[0].get("term") if tags else None
        if strategy == "from_path":
            # SME encodes the section as the first path segment:
            # https://www.sme.sk/<section>/c/... -> "<section>"
            try:
                segments = urlparse(url).path.split("/")
                return next((s for s in segments if s), None)
            except (AttributeError, TypeError):
                return None
        return None  # "none" or unknown
