# spravomat/orchestration/collect.py

"""
Run 1 — collection. Frequent (hourly via host cron on the VPS), as
`docker compose run --rm batch python -m spravomat.orchestration.collect`.

    acquisition.run()  ->  retention (delete articles older than RETENTION_DAYS)

Sequential fail-fast: if acquisition fails, retention is skipped (harmless — it
runs next cycle). Entry point: `python -m spravomat.orchestration.collect`.
"""

import sys

from spravomat import acquisition
from spravomat.db import repository
from spravomat.orchestration import run_steps
from spravomat.shared.logging import setup_logging

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
    setup_logging()
    sys.exit(main())
