# spravomat/web/__init__.py

"""
Web component — the dumb-render layer.

Reads finished story cards from db and renders them as one HTML page. No
business logic, no joins, no data decisions: everything is baked into the cards
by presentation. Exposes the Flask application factory create_app().
"""

from flask import Flask

from spravomat.web import routes
from spravomat.web.filters import register_filters


def create_app() -> Flask:
    """
    Build and configure the Flask app.

    Templates and static files default to web/templates and web/static.

    Returns:
        The configured Flask application.
    """
    app = Flask(__name__)
    register_filters(app)
    app.register_blueprint(routes.bp)
    return app
