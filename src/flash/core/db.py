"""Database Module"""

from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from flash.core.config import get_settings

engine = create_async_engine(
    get_settings().database_url,
    echo=get_settings().debug,
    pool_size=get_settings().db_pool_size,
    max_overflow=get_settings().db_max_overflow,
    pool_timeout=get_settings().db_pool_timeout,
    pool_recycle=get_settings().db_pool_recycle,
    pool_pre_ping=get_settings().db_pool_pre_ping,
)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class that all models inherit from"""

    id: Mapped[int] = mapped_column(primary_key=True)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Yield-dependency: provides a session per request, closes it after."""
    async with async_session_maker() as session:
        yield session
