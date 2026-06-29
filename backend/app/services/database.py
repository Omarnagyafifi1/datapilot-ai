from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from typing import AsyncGenerator

# Create async engine for PostgreSQL (only if DATABASE_URL is configured)
_db_url = settings.DATABASE_URL.strip()
engine = create_async_engine(_db_url, echo=False) if _db_url else None

# Session factory for dependencies if needed later
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

