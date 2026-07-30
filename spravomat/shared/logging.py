# spravomat/shared/logging.py

"""
Cross-cutting logging setup.

One place that decides how Spravomat logs, so every entry point looks the same.
Logs go to stdout: containers treat stdout as the log stream, and the batch
wrapper script captures it to a per-run file before `--rm` discards the
container (see plans/logging.md).

Entry points call setup_logging() once at startup; library modules never
configure logging, they just use logging.getLogger(__name__).
"""

import logging
import sys

# Logger name is in the format on purpose: it answers "where did this come
# from" (spravomat.acquisition.rss vs spravomat.db.repository) without opening
# the code. The full date is there so an append-only log file spanning weeks
# stays readable.
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Third-party libraries that log at INFO and drown out our own lines.
NOISY_LOGGERS = (
    "urllib3",
    "httpx",
    "httpcore",
    "sentence_transformers",
    "transformers",
    "filelock",
)


def setup_logging(level: str | None = None) -> None:
    """
    Configure root logging for stdout.

    Idempotent: existing root handlers are removed first, so calling this twice
    (or after a library has configured logging) does not duplicate every line.

    Args:
        level: Level name override (e.g. "DEBUG"). Defaults to
            config.LOG_LEVEL. An unrecognised name falls back to INFO rather
            than raising — bad config should not stop the pipeline from running.
    """
    # Imported here, not at module top, to keep the import graph one-directional:
    # config must not end up importing logging setup back.
    from spravomat.shared import config

    level_name = (level or config.LOG_LEVEL).upper()
    resolved = getattr(logging, level_name, None)
    unknown_level = not isinstance(resolved, int)
    if unknown_level:
        resolved = logging.INFO

    root = logging.getLogger()
    for existing in root.handlers[:]:
        root.removeHandler(existing)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(resolved)

    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    if unknown_level:
        logging.getLogger(__name__).warning(
            f"⚠️ Unknown LOG_LEVEL '{level_name}', falling back to INFO"
        )
