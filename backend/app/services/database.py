from __future__ import annotations

import threading
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Guards engine creation so concurrent threads don't all try to initialize
# SQLite pragmas (e.g. PRAGMA journal_mode=WAL) on the same file at once.
_engine_lock = threading.Lock()


def _configure_sqlite_connect_args(url: str) -> dict:
    """Connection args that let one connection be safely shared across threads."""
    if _is_sqlite_url(url):
        return {"timeout": 30, "check_same_thread": False}
    return {}


def _set_busy_timeout_on_connect(dbapi_conn, connection_record) -> None:
    """Set a generous busy_timeout on every new SQLite connection so concurrent
    access waits instead of immediately raising 'database is locked'."""
    try:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
    except Exception:  # pragma: no cover - best effort
        pass


def _attach_sqlite_listeners(engine: Engine) -> None:
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _set_busy_timeout_on_connect)


# ── Async engine (for optional async use) ──────────────────────────────

_db_url = str(getattr(settings, 'DATABASE_URL', '') or '').strip()

async_engine = None
if _db_url:
    try:
        async_engine = create_async_engine(_db_url, echo=False)
    except Exception as e:
        logger.warning("Failed to create async engine: %s", e)
        async_engine = None

AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession) if async_engine else None

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    if AsyncSessionLocal is None:
        raise RuntimeError("DATABASE_URL not configured")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Shared sync engine (used by internal services) ─────────────────────
# All services (data_source_service, history_service, llm_settings_service,
# chat_repository) use this single engine. If DATABASE_URL is set (PostgreSQL
# in production), use it. Otherwise fall back to individual SQLite URLs.

_SYNC_ENGINE: Optional[Engine] = None


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite") or url.startswith("sqlite+aiosqlite")


def _set_sqlite_pragmas(engine: Engine) -> None:
    """Enable WAL mode and sensible pragmas.

    PRAGMA journal_mode=WAL requires a brief exclusive lock. We retry it a few
    times (with a generous busy_timeout already configured on connect) so that
    concurrent initialization attempts don't fail with 'database is locked'.
    """
    import time

    last_err: Optional[Exception] = None
    for attempt in range(10):
        try:
            with engine.connect() as conn:
                conn.execution_options(isolation_level="AUTOCOMMIT")
                conn.execute(text("PRAGMA busy_timeout=30000"))
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA synchronous=NORMAL"))
                conn.commit()
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(0.2 * (attempt + 1))
    if last_err:
        logger.warning("Could not set SQLite WAL pragmas after retries: %s", last_err)

def get_sync_engine() -> Engine:
    """Return a shared sync engine for internal application state.

    Production: uses DATABASE_URL (PostgreSQL) — all tables in one DB.
    Development: uses DATA_SOURCES_DB_URL (SQLite) — maintains backward compat.
    """
    global _SYNC_ENGINE
    if _SYNC_ENGINE is not None:
        return _SYNC_ENGINE

    # Serialize engine creation so two threads don't race to run the WAL pragma.
    with _engine_lock:
        if _SYNC_ENGINE is not None:
            return _SYNC_ENGINE

        db_url = str(settings.DATABASE_URL or "").strip()
        if db_url and not _is_sqlite_url(db_url):
            # Production — single PostgreSQL database for all internal state
            if db_url.startswith("postgresql+asyncpg://"):
                db_url = "postgresql+psycopg2://" + db_url[len("postgresql+asyncpg://"):]

            _SYNC_ENGINE = create_engine(
                db_url,
                pool_pre_ping=True,
            )
            logger.info("Shared sync engine: PostgreSQL (%s)", db_url.split("@")[-1] if "@" in db_url else "configured")
        else:
            # Development — use DATA_SOURCES_DB_URL (SQLite).
            # Engine creation is serialized via _engine_lock so the WAL pragma
            # is never run by two threads at once. A generous busy_timeout (set
            # on connect) makes concurrent access wait instead of erroring.
            sqlite_url = str(getattr(settings, 'data_sources_db_url', 'sqlite:///./data_sources.db'))
            if _is_sqlite_url(sqlite_url):
                _SYNC_ENGINE = create_engine(
                    sqlite_url,
                    pool_pre_ping=True,
                    connect_args=_configure_sqlite_connect_args(sqlite_url),
                )
                _attach_sqlite_listeners(_SYNC_ENGINE)
                _set_sqlite_pragmas(_SYNC_ENGINE)
            else:
                _SYNC_ENGINE = create_engine(
                    sqlite_url,
                    pool_pre_ping=True,
                    connect_args={"timeout": 30},
                )
            logger.info("Shared sync engine: SQLite (%s)", sqlite_url)

    return _SYNC_ENGINE


_HISTORY_ENGINE: Optional[Engine] = None


def get_sync_engine_for_history() -> Engine:
    """Return engine for query history.

    Production: same as get_sync_engine() (PostgreSQL).
    Development: separate SQLite file (backward compat).
    """
    global _HISTORY_ENGINE
    db_url = str(settings.DATABASE_URL or "").strip()
    if db_url and not _is_sqlite_url(db_url):
        return get_sync_engine()

    if _HISTORY_ENGINE is not None:
        return _HISTORY_ENGINE

    with _engine_lock:
        if _HISTORY_ENGINE is not None:
            return _HISTORY_ENGINE
        sqlite_url = str(getattr(settings, 'query_history_db_url', 'sqlite:///./query_history.db'))
        if _is_sqlite_url(sqlite_url):
            _HISTORY_ENGINE = create_engine(
                sqlite_url,
                pool_pre_ping=True,
                connect_args=_configure_sqlite_connect_args(sqlite_url),
            )
            _attach_sqlite_listeners(_HISTORY_ENGINE)
            _set_sqlite_pragmas(_HISTORY_ENGINE)
        else:
            _HISTORY_ENGINE = create_engine(
                sqlite_url,
                pool_pre_ping=True,
                connect_args={"timeout": 30},
            )
    return _HISTORY_ENGINE


def dispose_sync_engine() -> None:
    """Dispose the shared sync engine (for tests / reset)."""
    global _SYNC_ENGINE
    if _SYNC_ENGINE is not None:
        try:
            _SYNC_ENGINE.dispose()
        except Exception:
            pass
        _SYNC_ENGINE = None

