# spravomat/acquisition/__init__.py

"""
Acquisition component — fetch, normalize, and store Slovak news articles.

Public API: run(). Everything else (RSSFetcher, PerexScraper, source specs) is
internal and hidden behind this entry point.
"""

from spravomat.acquisition.runner import run

__all__ = ["run"]
