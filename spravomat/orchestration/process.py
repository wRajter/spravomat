# spravomat/orchestration/process.py

"""
Run 2 — processing. A few times a day via host cron on the VPS (e.g. 06/12/18
UTC), as `docker compose run --rm batch python -m spravomat.orchestration.process`.

    grouping.run()  ->  presentation.run()

Sequential fail-fast: if grouping fails, presentation is skipped. Grouping always
receives already-bounded data (retention runs in collection). Entry point:
`python -m spravomat.orchestration.process`.
"""

import logging
import sys

from spravomat import grouping, presentation
from spravomat.orchestration import run_steps
from spravomat.shared import config


def main() -> int:
    """Run processing; return a process exit code (0 ok, 1 failed)."""
    result = run_steps(
        "process",
        [
            ("grouping", grouping.run),
            ("presentation", presentation.run),
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
