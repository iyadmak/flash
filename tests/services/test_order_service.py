"""Unit tests for OrderService — no DB, no HTTP, just the service against fakes."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from redis.exceptions import LockError

from flash.core.exceptions import DuplicateRequest
from flash.models.order_model import OrderModel
from flash.schemas.order_schema import OrderCreate
from flash.services.order_service import OrderService


class FakeOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[int, OrderModel] = {}
        self._next_id = 1
        self.create_started = asyncio.Event()
        self.allow_create = asyncio.Event()
        self.create_calls = 0
        self.commit_calls = 0

    async def get(self, id: int) -> OrderModel | None:
        return self._orders.get(id)

    async def list(self, limit: int, offset: int) -> list[OrderModel]:
        return list(self._orders.values())[offset : offset + limit]

    async def create(self, instance: OrderModel) -> OrderModel:
        self.create_calls += 1
        self.create_started.set()
        await self.allow_create.wait()
        instance.id = self._next_id
        self._next_id += 1
        self._orders[instance.id] = instance
        return instance

    async def delete(self, instance: OrderModel) -> None:
        self._orders.pop(instance.id, None)

    async def commit(self) -> None:
        self.commit_calls += 1

    async def refresh(self, instance: OrderModel) -> None:
        pass


class FakeLockClient:
    def __init__(self) -> None:
        self._locked: set[str] = set()
        self.calls: list[tuple[str, float | None, bool]] = []

    @asynccontextmanager
    async def _acquire(self, name: str) -> AsyncIterator[None]:
        if name in self._locked:
            raise LockError("Unable to acquire lock within the time specified")  # type: ignore[no-untyped-call]
        self._locked.add(name)
        try:
            yield
        finally:
            self._locked.discard(name)

    def lock(
        self, name: str, *, timeout: float | None = None, blocking: bool = True
    ) -> Any:
        self.calls.append((name, timeout, blocking))
        return self._acquire(name)


@pytest.fixture
def repo() -> FakeOrderRepository:
    return FakeOrderRepository()


@pytest.fixture
def lock_client() -> FakeLockClient:
    return FakeLockClient()


@pytest.fixture
def service(repo: FakeOrderRepository, lock_client: FakeLockClient) -> OrderService:
    return OrderService(repo, lock_client)


class TestCreate:
    async def test_raises_duplicate_request_when_same_order_create_is_locked(
        self,
        service: OrderService,
        repo: FakeOrderRepository,
        lock_client: FakeLockClient,
    ) -> None:
        data = OrderCreate(
            user_id=1, restaurant_id=2, total_price=42.50, status="pending"
        )

        first_create = asyncio.create_task(service.create(data))
        try:
            await asyncio.wait_for(repo.create_started.wait(), timeout=1)

            with pytest.raises(DuplicateRequest):
                await service.create(data)
        finally:
            repo.allow_create.set()

        created = await first_create

        assert created.id == 1
        assert repo.create_calls == 1
        assert repo.commit_calls == 1
        assert lock_client.calls == [
            ("order_lock:user:1:restaurant:2", 10, False),
            ("order_lock:user:1:restaurant:2", 10, False),
        ]
