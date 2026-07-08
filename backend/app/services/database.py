from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from typing import AsyncGenerator


_db_url = settings.get_resolved_database_url()

engine = None
if _db_url:
    try:
        engine = create_async_engine(_db_url, echo=False, pool_size=5, max_overflow=10, pool_pre_ping=True)
    except Exception as e:
        print(f"Warning: Failed to create async engine: {e}")
        engine = None

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession) if engine else None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not configured")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
