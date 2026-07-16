# spravomat/presentation/enrichment.py

"""
Story enrichment — producing a title and bullets for a cluster.

The provider is hidden behind the `Enricher` interface so it can be swapped
without touching the rest of presentation. v1 ships `KeywordEnricher` (title
from TF-IDF keywords, no bullets); a concrete LLM enricher slots in later as a
new `Enricher` and can use `KeywordEnricher` as its failure fallback.
"""

import logging
from abc import ABC, abstractmethod

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from spravomat.presentation import config
from spravomat.presentation.ranking import Cluster

logger = logging.getLogger(__name__)


class Enricher(ABC):
    """Strategy for turning a cluster into a story title and bullets."""

    @abstractmethod
    def enrich(self, cluster: Cluster) -> dict:
        """
        Produce enrichment for a cluster.

        Returns:
            {"title": str, "bullets": list[str]}.
        """
        ...


class KeywordEnricher(Enricher):
    """
    v1 enricher: title from the cluster's top TF-IDF keywords, no bullets.

    Also the fallback for a future LLM enricher when the model call fails.
    """

    def enrich(self, cluster: Cluster) -> dict:
        titles = [a.title for a in cluster.articles if a.title]
        keywords = _extract_keywords(titles)
        title = ", ".join(keywords) if keywords else (titles[0] if titles else "")
        return {"title": title, "bullets": []}


def _extract_keywords(titles: list[str], top_n: int = config.KEYWORD_TOP_N) -> list[str]:
    """
    Extract the top keywords across a set of titles via TF-IDF.

    Returns an empty list if there are fewer than 2 titles (TF-IDF needs
    multiple documents to tell what is distinctive) or if extraction fails.
    """
    if len(titles) < 2:
        return []
    try:
        vectorizer = TfidfVectorizer(stop_words=config.SK_STOP_WORDS)
        tfidf = vectorizer.fit_transform(titles)
        features = vectorizer.get_feature_names_out()
        avg_scores = np.asarray(tfidf.mean(axis=0)).ravel()
        top_indices = avg_scores.argsort()[-top_n:][::-1]
        return [features[i] for i in top_indices]
    except Exception as e:
        logger.warning(f"⚠️ Keyword extraction failed: {e}")
        return []
