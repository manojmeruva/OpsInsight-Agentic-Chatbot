"""
Centralized StarRocks connection pool using SQLAlchemy QueuePool.

For local runs set DATA_DB_ENGINE=sqlite: get_connection() then yields a
read-only sqlite3 connection to Config.SQLITE_DATA_DB_PATH instead.

Usage:
    from core.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
"""

import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from urllib.parse import quote_plus

from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool
from config import Config

logger = logging.getLogger(__name__)

_engine = None
_lock = threading.Lock()


def _build_engine():
    db = Config.get_db_config()
    password_part = f":{quote_plus(db['password'])}" if db.get("password") else ""
    url = (
        f"mysql+pymysql://{db['user']}{password_part}"
        f"@{db['host']}:{db['port']}/{db['database']}"
    )

    engine = create_engine(
        url,
        poolclass=QueuePool,
        pool_size=Config.POOL_SIZE,
        max_overflow=Config.POOL_MAX_OVERFLOW,
        pool_recycle=Config.POOL_RECYCLE_SECONDS,
        pool_pre_ping=Config.POOL_PRE_PING,
        pool_timeout=30,
    )

    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_conn, connection_record, connection_proxy):
        logger.debug("Pool checkout: %s", id(dbapi_conn))

    @event.listens_for(engine, "checkin")
    def on_checkin(dbapi_conn, connection_record):
        logger.debug("Pool checkin: %s", id(dbapi_conn))

    logger.info(
        "StarRocks connection pool created: pool_size=%d, max_overflow=%d, recycle=%ds",
        Config.POOL_SIZE, Config.POOL_MAX_OVERFLOW, Config.POOL_RECYCLE_SECONDS,
    )
    return engine


def get_engine():
    """Return the singleton SQLAlchemy engine (lazy-initialized, thread-safe)."""
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = _build_engine()
    return _engine


def is_sqlite() -> bool:
    return Config.DATA_DB_ENGINE == "sqlite"


@contextmanager
def _sqlite_connection():
    path = os.path.abspath(Config.SQLITE_DATA_DB_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"SQLite data DB not found at {path}. Check SQLITE_DATA_DB_PATH."
        )
    # Read-only: generated code must never modify data
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_connection():
    """
    Yield a raw pymysql DBAPI connection from the pool.

    The connection is returned to the pool (not destroyed) when the
    context manager exits.
    """
    if is_sqlite():
        with _sqlite_connection() as conn:
            yield conn
        return

    engine = get_engine()
    raw_conn = engine.raw_connection()
    try:
        yield raw_conn
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()  # returns to pool, does NOT destroy


def dispose_pool():
    """Shutdown the pool (call on app shutdown)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        logger.info("StarRocks connection pool disposed.")
        _engine = None
