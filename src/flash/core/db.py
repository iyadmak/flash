"""Database Module"""

from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker, create_async_engine)
from sqlalchemy.orm import DeclarativeBase
from flash.core.config import get_settings

engine = create_async_engine(get_settings().database_url, echo=get_settings().debug)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    """ Base class that all models inherit from """

async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Yield-dependency: provides a session per request, closes it after."""
    async with async_session_maker() as session:
        yield session
