# spravomat/presentation/enrichment.py

"""
Story enrichment — producing a title and bullets for a cluster.

The provider is hidden behind the `Enricher` interface so it can be swapped
without touching the rest of presentation. v1 ships `KeywordEnricher` (title
from TF-IDF keywords, no bullets); a concrete LLM enricher slots in later as a
new `Enricher` and can use `KeywordEnricher` as its failure fallback.
"""

import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from spravomat.presentation import config
from spravomat.presentation.prompts import ENRICHMENT_PROMPT
from spravomat.presentation.ranking import Cluster

logger = logging.getLogger(__name__)

# Prompt-size bounds (cost/latency safety; real clusters are small anyway).
_MAX_ARTICLES = 8         # articles fed per cluster
_MAX_TEXT_CHARS = 600     # per-article summary+perex length


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


class GeminiEnricher(Enricher):
    """
    Default enricher: generates the title + bullets with Gemini from each
    cluster's article texts (title + summary + perex).

    Resilient per card: on any failure (API error, timeout, unparseable reply)
    after RETRY_COUNT attempts, it delegates to a KeywordEnricher for THAT card
    only (keyword title + empty bullets). One bad card never aborts the run.
    """

    def __init__(self):
        self._fallback = KeywordEnricher()

    def enrich(self, cluster: Cluster) -> dict:
        prompt = ENRICHMENT_PROMPT.format(articles=_build_article_blocks(cluster))

        for attempt in range(config.ENRICH_RETRY_COUNT):
            try:
                result = _parse_enrichment(self._call(prompt))
                if result is not None:
                    return result
                logger.warning(
                    f"⚠️ Enrichment: unparseable reply for cluster "
                    f"{cluster.cluster_id} (attempt {attempt + 1})"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Enrichment call failed for cluster "
                    f"{cluster.cluster_id} (attempt {attempt + 1}): {e}"
                )
            if attempt < config.ENRICH_RETRY_COUNT - 1:
                time.sleep(0.5 * (2 ** attempt))  # short backoff: 0.5s, 1s, ...

        logger.error(
            f"❌ Enrichment failed for cluster {cluster.cluster_id} after "
            f"{config.ENRICH_RETRY_COUNT} attempts — using keyword fallback"
        )
        return self._fallback.enrich(cluster)

    def _call(self, prompt: str) -> str:
        """Call Gemini and return the raw text. Imported lazily to keep imports light."""
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY"),
            http_options=types.HttpOptions(timeout=int(config.ENRICH_TIMEOUT * 1000)),
        )
        response = client.models.generate_content(
            model=config.ENRICH_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=config.ENRICH_TEMPERATURE,
                max_output_tokens=config.ENRICH_MAX_TOKENS,
            ),
        )
        return response.text or ""


def get_enricher() -> Enricher:
    """
    Pick the enricher for this run: Gemini when GEMINI_API_KEY is set, otherwise
    the keyword fallback. Keeps the app working without an LLM (never crashes on
    a missing key).
    """
    if os.getenv("GEMINI_API_KEY"):
        logger.info("ℹ️ Enrichment: using GeminiEnricher (LLM)")
        return GeminiEnricher()
    logger.info("ℹ️ Enrichment: GEMINI_API_KEY not set — using KeywordEnricher (fallback)")
    return KeywordEnricher()


def _build_article_blocks(cluster: Cluster) -> str:
    """One block per article (title + summary/perex text) for the prompt."""
    blocks = []
    for article in cluster.articles[:_MAX_ARTICLES]:
        parts = [p for p in (article.summary, article.perex) if p]
        text = " ".join(parts)[:_MAX_TEXT_CHARS] or "(bez textu)"
        blocks.append(f"- Titulok: {article.title}\n  Text: {text}")
    return "\n".join(blocks)


def _parse_enrichment(text: str) -> dict | None:
    """
    Parse the model's JSON reply into {"title", "bullets"}, tolerating ```json
    fences. Returns None if it can't be parsed or lacks a usable title.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    title = data.get("title")
    bullets = data.get("bullets")
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(bullets, list):
        return None
    return {"title": title.strip(), "bullets": [str(b) for b in bullets]}
