# spravomat/shared/config.py

"""
Cross-cutting configuration.

Loads environment variables (from a local .env in development; in production
Docker Compose injects them from the .env on the VPS) and exposes them as
module-level constants. Platform-specific values live here at the edge — the
only thing that switches local vs production is DATABASE_URL, via the
environment, never in code.
"""

import os

from dotenv import load_dotenv

# Load .env if present. When Compose has already injected the values into the
# container environment, this is a harmless no-op.
load_dotenv()

# Database connection string. Required by the db component. Left as None if
# unset so the db layer can raise a clear error at connection time.
DATABASE_URL: str | None = os.getenv("DATABASE_URL")

# Logging level name (e.g. "INFO", "DEBUG"). Defaults to INFO.
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Debug flag. True only for the literal "true" (case-insensitive).
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
