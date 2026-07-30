# spravomat/presentation/__main__.py

"""
Entry point for `python -m spravomat.presentation`.

Runs presentation once with logging set up, and exits non-zero if the run fails.
Handy for manual/dev runs; orchestration calls presentation.run() directly.
"""

import sys

from spravomat.presentation import run
from spravomat.shared.logging import setup_logging

setup_logging()

result = run()
print(result)
sys.exit(0 if result["success"] else 1)
