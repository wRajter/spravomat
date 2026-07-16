# spravomat/web/filters.py

"""
Jinja template filters — the only computation the web layer does.

- time_ago: absolute timestamp -> relative Slovak phrase, in Bratislava time.
  This is presentation relative to the moment of viewing, so it belongs here.
- medium_label: outlet key -> human-friendly display name.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask

_TZ = ZoneInfo("Europe/Bratislava")

# Human-friendly outlet names. Unknown keys fall back to the raw key.
MEDIUM_LABELS = {
    "sme": "SME",
    "aktuality": "Aktuality",
    "dennik_n": "Denník N",
    "teraz_sk": "Teraz.sk",
    "sita": "SITA",
    "24_hodin": "24hod",
    "euractiv": "Euractiv",
}


def time_ago(dt: datetime | None) -> str:
    """Relative Slovak phrase for how long ago `dt` was (Bratislava time)."""
    if dt is None:
        return ""
    hours = (datetime.now(_TZ) - dt).total_seconds() / 3600
    if hours < 1:
        return "pred chvíľou"
    if hours < 24:
        return f"pred {int(hours)} h"
    return f"pred {int(hours / 24)} dňami"


def medium_label(key: str) -> str:
    """Human-friendly outlet name for a medium key, or the raw key if unknown."""
    return MEDIUM_LABELS.get(key, key)


def register_filters(app: Flask) -> None:
    """Register the web template filters on the Flask app."""
    app.add_template_filter(time_ago)
    app.add_template_filter(medium_label)
