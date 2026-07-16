# spravomat/web/routes/__init__.py

"""
Web routes — the single home page.

Dumb render: read the finished story cards from db and hand them to the
template. On a read failure, fall back to an empty list so the page shows the
empty state (the error is already logged in the repository).
"""

import logging

from flask import Blueprint, render_template

from spravomat.db import repository

logger = logging.getLogger(__name__)

bp = Blueprint("web", __name__)


@bp.route("/")
def home():
    """Render the list of story cards, highest-ranked first."""
    result = repository.get_story_cards()
    cards = result["data"] if result["success"] else []
    return render_template("home.html", cards=cards)
