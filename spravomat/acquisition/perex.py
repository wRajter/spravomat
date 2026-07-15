# spravomat/acquisition/perex.py

"""
Per-source perex scraping.

The perex (lead paragraph) is usually absent from RSS feeds, so it is scraped
from each article's page. Scraping is inherently per-site: every outlet marks
its perex with a different CSS selector, and some need special handling. This
module keeps the POC's per-domain dispatch — one small method per site holding
only that site's selector — rather than generalizing logic that is genuinely
different per source.

Perex is best-effort: an unsupported medium, a blocked request, or a missing
element all yield None, and the article simply keeps a null perex.
"""

import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# HTTP timeout (seconds) for fetching an article page.
PEREX_REQUEST_TIMEOUT = 10

# Politeness delay (seconds) between perex requests. Applied by the caller
# (the acquisition runner) when looping over articles, not by the scraper itself.
PEREX_RATE_LIMIT_SECONDS = 0.5


class PerexScraper:
    """
    Scrapes the perex from a Slovak news article page, dispatching by domain.

    Supported media: SME, Aktuality (incl. sport.aktuality.sk), Denník N,
    Teraz.sk, SITA, 24hodín, Euractiv.

    Example:
        >>> scraper = PerexScraper()
        >>> scraper.get_perex("https://www.sme.sk/c/some-article")
        "Lead paragraph text..."

    Attributes:
        timeout: HTTP request timeout in seconds.
        headers: Default HTTP headers.
        extended_headers: Richer headers for sites with stricter bot protection.
    """

    def __init__(self, timeout: int = PEREX_REQUEST_TIMEOUT):
        """
        Initialize the scraper.

        Args:
            timeout: Maximum time to wait for a server response, in seconds.
        """
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        self.extended_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "sk,en;q=0.5",
            "Connection": "keep-alive",
        }

        # Domain -> per-source scraping method.
        self._scrapers = {
            "sme.sk": self._get_sme_perex,
            "aktuality.sk": self._get_aktuality_perex,
            "dennikn.sk": self._get_dennikn_perex,
            "teraz.sk": self._get_teraz_perex,
            "sita.sk": self._get_sita_perex,
            "24hod.sk": self._get_24hodin_perex,
            "euractiv.sk": self._get_euractiv_perex,
        }

    # ====================
    # Public API
    # ====================

    def get_perex(self, url: str) -> str | None:
        """
        Scrape the perex for an article URL.

        Recognizes the medium from the URL and dispatches to the matching
        method. Best-effort: returns None for an unsupported medium or on any
        failure (never raises).

        Args:
            url: Full article URL.

        Returns:
            The perex text, or None if unsupported / not found / failed.
        """
        try:
            for domain, scraper_method in self._scrapers.items():
                if domain in url:
                    return scraper_method(url)
            logger.debug(f"🐞 Unsupported medium for perex: {url}")
            return None
        except Exception as e:
            logger.error(f"❌ Perex scrape failed for {url}: {e}")
            return None

    def is_supported(self, url: str) -> bool:
        """Return True if a scraping method exists for this URL's domain."""
        return any(domain in url for domain in self._scrapers)

    # ====================
    # Private helpers
    # ====================

    def _fetch_page(self, url: str, use_extended_headers: bool = False) -> BeautifulSoup | None:
        """
        Fetch and parse an article page.

        Args:
            url: Page URL.
            use_extended_headers: If True, use the richer headers for sites with
                stricter bot protection.

        Returns:
            A BeautifulSoup document, or None on request failure.
        """
        headers = self.extended_headers if use_extended_headers else self.headers
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException:
            return None

    def _extract_text(self, element) -> str | None:
        """Safely extract stripped text from a BeautifulSoup element, or None."""
        if element:
            return element.get_text().strip()
        return None

    # ====================
    # Per-source methods (hold only that site's selector / special case)
    # ====================

    def _get_sme_perex(self, url: str) -> str | None:
        """SME.sk — first <p> in div.article-body."""
        soup = self._fetch_page(url)
        if not soup:
            return None
        article_body = soup.find("div", class_="article-body")
        if article_body:
            return self._extract_text(article_body.find("p"))
        return None

    def _get_aktuality_perex(self, url: str) -> str | None:
        """
        Aktuality.sk — span[itemprop=description] on the main domain; the sport
        subdomain (sport.aktuality.sk) uses h5 in div.row.single-news-content.
        """
        soup = self._fetch_page(url)
        if not soup:
            return None
        if "sport.aktuality.sk" in url:
            content = soup.find("div", class_="row single-news-content")
            if content:
                return self._extract_text(content.find("h5"))
            return None
        return self._extract_text(soup.find("span", itemprop="description"))

    def _get_dennikn_perex(self, url: str) -> str | None:
        """Denník N — first <p> in div.n3_content."""
        soup = self._fetch_page(url)
        if not soup:
            return None
        article_body = soup.find("div", class_="n3_content")
        if article_body:
            return self._extract_text(article_body.find("p"))
        return None

    def _get_teraz_perex(self, url: str) -> str | None:
        """Teraz.sk — p.articlePerex."""
        soup = self._fetch_page(url)
        if not soup:
            return None
        return self._extract_text(soup.find("p", class_="articlePerex"))

    def _get_sita_perex(self, url: str) -> str | None:
        """SITA — div.entry-excerpt."""
        soup = self._fetch_page(url)
        if not soup:
            return None
        return self._extract_text(soup.find("div", class_="entry-excerpt"))

    def _get_24hodin_perex(self, url: str) -> str | None:
        """24hodín.sk — first paragraph of div#clanok_text01 (split on blank line)."""
        soup = self._fetch_page(url)
        if not soup:
            return None
        article_body = soup.find("div", id="clanok_text01")
        if article_body:
            text = article_body.get_text().strip()
            return text.split("\n\n")[0].strip()
        return None

    def _get_euractiv_perex(self, url: str) -> str | None:
        """Euractiv.sk — first <p> in div.ea-article-body-content (needs extended headers)."""
        soup = self._fetch_page(url, use_extended_headers=True)
        if not soup:
            return None
        article_body = soup.find("div", class_="ea-article-body-content")
        if article_body:
            return self._extract_text(article_body.find("p"))
        return None
