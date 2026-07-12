"""Shared test fixtures: DB setup, per-test session, and async HTTP client."""

import os
from typing import cast

import pytest
import pytest_asyncio
from collections.abc import Iterator, AsyncIterator
from alembic import command
from alembic.config import Config
from testcontainers.postgres import PostgresContainer
from httpx import AsyncClient, ASGITransport
from limits.aio.storage import MemoryStorage
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from flash.core.db import get_async_session
from flash.core.config import get_settings
from flash.core.cache import get_user_cache
from flash.core.rate_limit import get_rate_limit_storage
from flash.main import app


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as container:
        yield container


@pytest.fixture(scope="session")
def db_url(postgres_container: PostgresContainer) -> str:
    return cast(str, postgres_container.get_connection_url())


@pytest.fixture(scope="session")
def run_migrations(db_url: str) -> None:
    os.environ["REAL_DATABASE_URL"] = db_url
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")


@pytest_asyncio.fixture
async def async_engine(db_url: str, run_migrations: None) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(db_url)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with async_engine.connect() as conn:
        transaction = await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with session_factory() as session:
            yield session
            await transaction.rollback()


@pytest.fixture
async def client(async_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield async_session

    app.dependency_overrides[get_async_session] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


_test_rate_limit_storage = MemoryStorage()


@pytest.fixture(autouse=True)
async def reset_rate_limiter() -> None:
    app.dependency_overrides[get_rate_limit_storage] = lambda: _test_rate_limit_storage
    await _test_rate_limit_storage.reset()


class FakeCache:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    async def get(self, name: str, /) -> str | None:
        return self._data.get(name)

    async def set(self, name: str, value: str, ex: int | None = None) -> None:
        self._data[name] = value

    async def delete(self, *names: str) -> None:
        for name in names:
            self._data.pop(name, None)

    def clear(self) -> None:
        self._data.clear()


_test_user_cache = FakeCache()


@pytest.fixture(autouse=True)
async def reset_user_cache() -> None:
    app.dependency_overrides[get_user_cache] = lambda: _test_user_cache
    _test_user_cache.clear()
