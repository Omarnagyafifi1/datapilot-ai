from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from typing import AsyncGenerator

# Create async engine for PostgreSQL (only if DATABASE_URL is configured)
_db_url = getattr(settings, 'DATABASE_URL', None)
if not _db_url:
    _db_url = getattr(settings, 'database_url', None) or ''
_db_url = str(_db_url).strip()

engine = None
if _db_url:
    try:
        engine = create_async_engine(_db_url, echo=False)
    except Exception as e:
        print(f"Warning: Failed to create async engine: {e}")
        engine = None

# Session factory for dependencies if needed later
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

