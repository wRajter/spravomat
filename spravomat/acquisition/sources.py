# spravomat/acquisition/sources.py

"""
Declarative source specifications for RSS acquisition.

Each source is one `SourceSpec` literal. Per-source differences are expressed as
named *strategies* (plain data) — the actual extraction logic lives in the
generic loop in `rss.py`. Adding a source should mean adding a spec here, and
only touching `rss.py` if a genuinely new extraction pattern is needed.
"""

from dataclasses import dataclass


# HTTP User-Agent for feeds that block the default feedparser client
# (currently only Euractiv). Used when SourceSpec.use_headers is True.
FEED_USER_AGENT = "Mozilla/5.0"


@dataclass(frozen=True)
class SourceSpec:
    """
    Declarative description of one RSS source.

    Attributes:
        medium: Canonical outlet key (e.g. "sme"). Stored on every article and
            used for downstream media counts, so it must stay consistent.
        feeds: Mapping of {category_label: feed_url}. The label is used as the
            article category only when category_strategy is "from_feed_key"
            (multi-category sources like Aktuality/SITA); otherwise the label is
            None and a single feed URL is given.
        use_headers: If True, fetch the feed with FEED_USER_AGENT headers
            (needed by sources that block the default client).
        image_strategy: How to extract the image URL from a feed entry. One of:
            "links_by_type" — first image href in entry.links
            "image_url"     — entry["image_url"] (Aktuality, Denník N)
            "thumbnail"     — entry["thumbnail"] (SITA)
            "media_content" — entry["media_content"][0]["url"] (SME, Euractiv)
            "none"          — no image available
        category_strategy: How to extract the category. One of:
            "from_feed_key" — use the feeds mapping label (Aktuality, SITA)
            "from_tags"     — entry["tags"][0]["term"] (Denník N, Teraz.sk)
            "from_path"     — first path segment of the article URL (SME:
                              www.sme.sk/<section>/... -> "<section>")
            "none"          — no category available
        known_blocked: If True, the source is known to be blocked at the origin
            (e.g. Cloudflare 403) and expected to return no entries. An empty
            result is logged calmly at info level instead of as a warning, so a
            persistently blocked source does not spam the logs each run. Kept in
            the list so it self-heals if the block lifts.
    """

    medium: str
    feeds: dict[str | None, str]
    use_headers: bool = False
    image_strategy: str = "none"
    category_strategy: str = "none"
    known_blocked: bool = False


# ==========================================================================
# The 7 v1 sources. Feed URLs and per-source strategies mirror the POC.
# ==========================================================================

SOURCE_SPECS: list[SourceSpec] = [
    SourceSpec(
        medium="sme",
        feeds={None: "https://www.sme.sk/rss-title"},
        image_strategy="media_content",
        category_strategy="from_path",
    ),
    SourceSpec(
        medium="aktuality",
        feeds={
            "domace": "https://www.aktuality.sk/rss/domace/",
            "zahranicne": "https://www.aktuality.sk/rss/zahranicne/",
            "krimi": "https://www.aktuality.sk/rss/krimi/",
            "koktejl": "https://www.aktuality.sk/rss/koktejl/",
            "ekonomika": "https://www.aktuality.sk/rss/ekonomika/",
            "navyse": "https://www.aktuality.sk/rss/navyse/",
            "sport": "https://sport.aktuality.sk/api/rss",
        },
        image_strategy="image_url",
        category_strategy="from_feed_key",
    ),
    SourceSpec(
        medium="dennik_n",
        feeds={None: "https://dennikn.sk/feed"},
        image_strategy="image_url",
        category_strategy="from_tags",
    ),
    SourceSpec(
        medium="teraz_sk",
        feeds={None: "https://www.teraz.sk/rss/vsetky-spravy.rss"},
        image_strategy="none",
        category_strategy="from_tags",
    ),
    SourceSpec(
        medium="sita",
        feeds={
            "spravy": "https://sita.sk/kategoria/spravy/feed/",
            "sport": "https://sita.sk/kategoria/sport/feed/",
            "ekonomika": "https://sita.sk/kategoria/ekonomika/feed/",
            "futbal": "https://sita.sk/kategoria/sport/futbal/feed/",
            "tenis": "https://sita.sk/kategoria/sport/tenis/feed/",
            "hokej": "https://sita.sk/kategoria/sport/hokej/feed/",
            "motosport": "https://sita.sk/kategoria/sport/motor-sport/feed/",
            "hudba": "https://sita.sk/kategoria/kultura/hudba/feed/",
            "zdravie": "https://sita.sk/kategoria/zdravie/feed/",
            "veda_a_technika": "https://sita.sk/kategoria/veda-a-technika/feed/",
            "kultura": "https://sita.sk/kategoria/kultura/feed/",
            "knihy": "https://sita.sk/kategoria/kultura/knihy/feed/",
            "umenie": "https://sita.sk/kategoria/kultura/umenie/feed/",
            "film_a_tv": "https://sita.sk/kategoria/kultura/film-a-tv/feed/",
            "zaujimavosti": "https://sita.sk/kategoria/zaujimavosti/feed/",
            "zdravy_zivot": "https://sita.sk/kategoria/zdravie/zdravy-zivot/feed/",
            "ostatne": "https://sita.sk/kategoria/ostatne/feed/",
        },
        image_strategy="thumbnail",
        category_strategy="from_feed_key",
    ),
    SourceSpec(
        medium="24_hodin",
        feeds={None: "https://www.24hod.sk/rss/24hod.xml"},
        image_strategy="none",
        category_strategy="none",
    ),
    SourceSpec(
        medium="euractiv",
        feeds={None: "https://euractiv.sk/feed/"},
        use_headers=True,
        image_strategy="media_content",
        category_strategy="none",
        known_blocked=True,  # Cloudflare 403 as of 2026-07; kept so it self-heals
    ),
]
