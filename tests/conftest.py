"""Shared test fixtures: DB setup, per-test session, and async HTTP client."""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Any, cast

import pytest
import pytest_asyncio
from collections.abc import AsyncIterator, Iterator
from alembic import command
from alembic.config import Config
from testcontainers.postgres import PostgresContainer
from httpx import AsyncClient, ASGITransport
from limits.aio.storage import MemoryStorage
from redis.exceptions import LockError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from flash.core.db import get_async_session
from flash.core.config import get_settings
from flash.core.adapters.cache import get_user_cache
from flash.core.adapters.lock import get_lock_client
from flash.core.adapters.events import get_event_publisher
from flash.api.deps import get_event_stream_publisher
from flash.core.adapters.rate_limit import get_rate_limit_storage
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


class FakeLockClient:
    def __init__(self) -> None:
        self._locked: set[str] = set()

    @asynccontextmanager
    async def _acquire(self, name: str, blocking: bool) -> AsyncIterator[None]:
        if name in self._locked:
            if not blocking:
                raise LockError(  # type: ignore[no-untyped-call]
                    "Unable to acquire lock within the time specified"
                )
            while name in self._locked:
                await asyncio.sleep(0.01)
        self._locked.add(name)
        try:
            yield
        finally:
            self._locked.discard(name)

    def lock(
        self, name: str, *, timeout: float | None = None, blocking: bool = True
    ) -> Any:
        return self._acquire(name, blocking)

    def clear(self) -> None:
        self._locked.clear()


_test_lock_client = FakeLockClient()


@pytest.fixture(autouse=True)
async def reset_lock_client() -> None:
    app.dependency_overrides[get_lock_client] = lambda: _test_lock_client
    _test_lock_client.clear()


class FakeEventPublisher:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []

    def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        self.published.append((routing_key, payload))

    def clear(self) -> None:
        self.published.clear()


_test_event_publisher = FakeEventPublisher()


@pytest.fixture(autouse=True)
async def reset_event_publisher() -> None:
    app.dependency_overrides[get_event_publisher] = lambda: _test_event_publisher
    _test_event_publisher.clear()


class FakeEventStreamPublisher:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, dict[str, Any]]] = []

    async def publish(self, topic: str, key: str, payload: dict[str, Any]) -> None:
        self.published.append((topic, key, payload))

    def clear(self) -> None:
        self.published.clear()


_test_event_stream_publisher = FakeEventStreamPublisher()


@pytest.fixture(autouse=True)
async def reset_event_stream_publisher() -> None:
    app.dependency_overrides[get_event_stream_publisher] = lambda: (
        _test_event_stream_publisher
    )
    _test_event_stream_publisher.clear()
