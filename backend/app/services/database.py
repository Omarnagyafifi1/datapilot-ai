from __future__ import annotations

from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


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
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA busy_timeout=30000"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.commit()

def get_sync_engine() -> Engine:
    """Return a shared sync engine for internal application state.

    Production: uses DATABASE_URL (PostgreSQL) — all tables in one DB.
    Development: uses DATA_SOURCES_DB_URL (SQLite) — maintains backward compat.
    """
    global _SYNC_ENGINE
    if _SYNC_ENGINE is not None:
        return _SYNC_ENGINE

    db_url = str(settings.DATABASE_URL or "").strip()
    if db_url and not _is_sqlite_url(db_url):
        # Production — single PostgreSQL database for all internal state
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = "postgresql+psycopg2://" + db_url[len("postgresql+asyncpg://"):]

        connect_args: dict = {}
        _SYNC_ENGINE = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        logger.info("Shared sync engine: PostgreSQL (%s)", db_url.split("@")[-1] if "@" in db_url else "configured")
    else:
        # Development — use DATA_SOURCES_DB_URL (SQLite)
        sqlite_url = str(getattr(settings, 'data_sources_db_url', 'sqlite:///./data_sources.db'))
        _SYNC_ENGINE = create_engine(
            sqlite_url,
            pool_pre_ping=True,
            connect_args={"timeout": 30} if _is_sqlite_url(sqlite_url) else {},
        )
        if _is_sqlite_url(sqlite_url):
            _set_sqlite_pragmas(_SYNC_ENGINE)
        logger.info("Shared sync engine: SQLite (%s)", sqlite_url)

    return _SYNC_ENGINE


def get_sync_engine_for_history() -> Engine:
    """Return engine for query history.

    Production: same as get_sync_engine() (PostgreSQL).
    Development: separate SQLite file (backward compat).
    """
    db_url = str(settings.DATABASE_URL or "").strip()
    if db_url and not _is_sqlite_url(db_url):
        return get_sync_engine()
    sqlite_url = str(getattr(settings, 'query_history_db_url', 'sqlite:///./query_history.db'))
    return create_engine(
        sqlite_url,
        pool_pre_ping=True,
        connect_args={"timeout": 5},
    )


def dispose_sync_engine() -> None:
    """Dispose the shared sync engine (for tests / reset)."""
    global _SYNC_ENGINE
    if _SYNC_ENGINE is not None:
        try:
            _SYNC_ENGINE.dispose()
        except Exception:
            pass
        _SYNC_ENGINE = None

