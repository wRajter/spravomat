# spravomat/orchestration/__init__.py

"""
Orchestration component — run pipeline steps in order, on a schedule.

Adds no new functionality: it wires the existing components into sequential,
fail-fast runs. `run_steps` is the one shared piece; the two entry points
(collect, process) each define their step order and call it.
"""

import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)


def run_steps(pipeline_name: str, steps: list[tuple[str, Callable[[], dict]]]) -> dict:
    """
    Run steps in order, fail-fast.

    Each step is a `() -> standard dict` callable (exactly what the component
    run() functions are). If a step returns success=False, stop and report the
    failure; remaining steps do not run.

    A step that raises is treated as a failed step, not a crash: the traceback is
    logged and the standard failure dict is returned, so the caller always gets
    an exit code rather than an unhandled stack trace. Each step's duration is
    logged — it tells you whether a failure was slow (timeout) or instant.

    Args:
        pipeline_name: Label for logging (e.g. "collect").
        steps: Ordered (label, callable) pairs.

    Returns:
        Standard dict; success=True only if every step succeeded.
    """
    logger.info(f"🚀 {pipeline_name} started")
    pipeline_started = time.monotonic()

    for label, step in steps:
        step_started = time.monotonic()
        try:
            result = step()
        except Exception as error:
            elapsed = time.monotonic() - step_started
            message = f"{pipeline_name} crashed at {label} after {elapsed:.1f}s: {error}"
            # logger.exception attaches the traceback — the one thing you always
            # want when SSH-ing in after an alert.
            logger.exception(f"❌ {message}")
            return {"success": False, "message": message, "data": None}

        elapsed = time.monotonic() - step_started
        if not result["success"]:
            message = (
                f"{pipeline_name} failed at {label} after {elapsed:.1f}s: "
                f"{result['message']}"
            )
            logger.error(f"❌ {message}")
            return {"success": False, "message": message, "data": None}

        logger.info(f"✅ {label} ({elapsed:.1f}s): {result['message']}")

    total = time.monotonic() - pipeline_started
    logger.info(f"🏁 {pipeline_name} completed in {total:.1f}s")
    return {
        "success": True,
        "message": f"{pipeline_name} completed in {total:.1f}s",
        "data": None,
    }
