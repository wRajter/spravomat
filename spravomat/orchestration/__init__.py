# spravomat/orchestration/__init__.py

"""
Orchestration component — run pipeline steps in order, on a schedule.

Adds no new functionality: it wires the existing components into sequential,
fail-fast runs. `run_steps` is the one shared piece; the two entry points
(collect, process) each define their step order and call it.
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)


def run_steps(pipeline_name: str, steps: list[tuple[str, Callable[[], dict]]]) -> dict:
    """
    Run steps in order, fail-fast.

    Each step is a `() -> standard dict` callable (exactly what the component
    run() functions are). If a step returns success=False, stop and report the
    failure; remaining steps do not run.

    Args:
        pipeline_name: Label for logging (e.g. "collect").
        steps: Ordered (label, callable) pairs.

    Returns:
        Standard dict; success=True only if every step succeeded.
    """
    logger.info(f"🚀 {pipeline_name} started")
    for label, step in steps:
        result = step()
        if not result["success"]:
            message = f"{pipeline_name} failed at {label}: {result['message']}"
            logger.error(f"❌ {message}")
            return {"success": False, "message": message, "data": None}
        logger.info(f"✅ {label}: {result['message']}")
    logger.info(f"🏁 {pipeline_name} completed")
    return {"success": True, "message": f"{pipeline_name} completed", "data": None}
