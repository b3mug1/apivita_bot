from contextlib import asynccontextmanager
from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database.models import Base

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

engine: AsyncEngine = create_async_engine(
    settings.db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Context-manager & async-iterable helper
# ---------------------------------------------------------------------------

class SessionManager:
    """Supports both `async with get_session()` and `async for s in get_session()`."""
    def __init__(self):
        self._session = None

    async def __aenter__(self) -> AsyncSession:
        self._session = async_session_factory()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session is not None:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
            await self._session.close()

    async def __aiter__(self) -> AsyncGenerator[AsyncSession, None]:
        async with self as session:
            yield session


def get_session() -> SessionManager:
    """Provide a transactional database session compatible with both `async with` and `async for`."""
    return SessionManager()


# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Create all tables defined in the metadata (development / first-run helper).

    For production you should use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified successfully.")


async def close_db() -> None:
    """Dispose the engine connection pool gracefully on shutdown."""
    await engine.dispose()
    logger.info("Database connection pool disposed.")
