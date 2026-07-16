# spravomat/grouping/__init__.py

"""
Grouping component — cluster articles into stories (batch regime).

Public API: run(). Everything else (Clusterer, thresholds) is internal and
hidden behind this entry point.
"""

from spravomat.grouping.runner import run

__all__ = ["run"]
