# spravomat/presentation/__main__.py

"""
Entry point for `python -m spravomat.presentation`.

Runs presentation once with logging set up, and exits non-zero if the run fails.
Handy for manual/dev runs; orchestration calls presentation.run() directly.
"""

import logging
import sys

from spravomat.presentation import run
from spravomat.shared import config

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

result = run()
print(result)
sys.exit(0 if result["success"] else 1)
