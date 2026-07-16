# spravomat/orchestration/collect.py

"""
Run 1 — collection. Frequent (hourly on Heroku Scheduler).

    acquisition.run()  ->  retention (delete articles older than RETENTION_DAYS)

Sequential fail-fast: if acquisition fails, retention is skipped (harmless — it
runs next cycle). Entry point: `python -m spravomat.orchestration.collect`.
"""

import logging
import sys

from spravomat import acquisition
from spravomat.db import repository
from spravomat.orchestration import run_steps
from spravomat.shared import config

# Delete articles older than this many days (by fetched_at). The only
# orchestration knob; kept here since it is used only in this run.
RETENTION_DAYS = 3


def _retention() -> dict:
    """Retention step: drop articles older than RETENTION_DAYS."""
    return repository.delete_articles_older_than(RETENTION_DAYS)


def main() -> int:
    """Run collection; return a process exit code (0 ok, 1 failed)."""
    result = run_steps(
        "collect",
        [
            ("acquisition", acquisition.run),
            ("retention", _retention),
        ],
    )
    return 0 if result["success"] else 1


if __name__ == "__main__":
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    sys.exit(main())
