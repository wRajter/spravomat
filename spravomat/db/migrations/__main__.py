# spravomat/db/migrations/__main__.py

"""
Entry point for `python -m spravomat.db.migrations`. Run as a one-off compose
command on the VPS: `docker compose run --rm batch python -m spravomat.db.migrations`.

Applies the idempotent schema and exits non-zero on failure so a broken release
is caught.
"""

import logging
import sys

from spravomat.db.migrations import init_schema
from spravomat.shared import config

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(message)s",
)

result = init_schema()
sys.exit(0 if result["success"] else 1)
