# spravomat/db/connection.py

"""
Database connection management.

A single thin context manager that opens a psycopg 3 connection from
DATABASE_URL, commits on clean exit, rolls back on error, and always closes.
One connection per operation for now; connection pooling is a future
optimization. This is the only place that opens a database connection.
"""

import logging
from contextlib import contextmanager
from typing import Iterator

import psycopg

from spravomat.shared import config

logger = logging.getLogger(__name__)


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """
    Yield a database connection, committing on success and rolling back on error.

    Usage:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(...)

    Raises:
        RuntimeError: If DATABASE_URL is not configured.
    """
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set — cannot connect to the database.")

    conn = psycopg.connect(config.DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
