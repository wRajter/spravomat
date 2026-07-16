# spravomat/presentation/__init__.py

"""
Presentation component — rank clusters into display-ready story cards.

Public API: run(). Everything else (ranking, enrichment, card assembly) is
internal and hidden behind this entry point.
"""

from spravomat.presentation.runner import run

__all__ = ["run"]
