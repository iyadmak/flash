"""Unit tests for OrderService — no DB, no HTTP, just the service against fakes."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import pytest
from redis.exceptions import LockError

from flash.core.exceptions import DuplicateRequest, OrderNotFound
from flash.models.order_model import OrderModel
from flash.schemas.order_schema import OrderCreate, OrderUpdate
from flash.services.order_service import OrderService

ACTOR_ID = 1
OTHER_ACTOR_ID = 2


def an_order(user_id: int) -> OrderModel:
    return OrderModel(
        user_id=user_id, restaurant_id=2, total_price=42.50, status="pending"
    )


class FakeOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[int, OrderModel] = {}
        self._next_id = 1
        self.create_started = asyncio.Event()
        self.allow_create = asyncio.Event()
        self.create_calls = 0
        self.commit_calls = 0

    def seed(self, order: OrderModel) -> OrderModel:
        """Insert an order directly, bypassing the lock/publish path in
        OrderService.create -- for setting up orders owned by other users."""
        order.id = self._next_id
        self._next_id += 1
        order.created_at = order.updated_at = datetime.now(timezone.utc)
        self._orders[order.id] = order
        return order

    async def get(self, id: int) -> OrderModel | None:
        return self._orders.get(id)

    async def list_for_user(
        self, user_id: int, limit: int, offset: int
    ) -> list[OrderModel]:
        owned = [o for o in self._orders.values() if o.user_id == user_id]
        return owned[offset : offset + limit]

    async def create(self, instance: OrderModel) -> OrderModel:
        self.create_calls += 1
        self.create_started.set()
        await self.allow_create.wait()
        instance.id = self._next_id
        self._next_id += 1
        instance.created_at = instance.updated_at = datetime.now(timezone.utc)
        self._orders[instance.id] = instance
        return instance

    async def delete(self, instance: OrderModel) -> None:
        self._orders.pop(instance.id, None)

    async def commit(self) -> None:
        self.commit_calls += 1

    async def refresh(self, instance: OrderModel) -> None:
        pass


class FakeEventPublisher:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []

    def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        self.published.append((routing_key, payload))


class FakeEventStreamPublisher:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, dict[str, Any]]] = []

    async def publish(self, topic: str, key: str, payload: dict[str, Any]) -> None:
        self.published.append((topic, key, payload))


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
def event_publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def event_stream_publisher() -> FakeEventStreamPublisher:
    return FakeEventStreamPublisher()


@pytest.fixture
def service(
    repo: FakeOrderRepository,
    lock_client: FakeLockClient,
    event_publisher: FakeEventPublisher,
    event_stream_publisher: FakeEventStreamPublisher,
) -> OrderService:
    return OrderService(repo, lock_client, event_publisher, event_stream_publisher)


class TestCreate:
    async def test_raises_duplicate_request_when_same_order_create_is_locked(
        self,
        service: OrderService,
        repo: FakeOrderRepository,
        lock_client: FakeLockClient,
    ) -> None:
        data = OrderCreate(restaurant_id=2, total_price=42.50, status="pending")

        first_create = asyncio.create_task(service.create(data, ACTOR_ID))
        try:
            await asyncio.wait_for(repo.create_started.wait(), timeout=1)

            with pytest.raises(DuplicateRequest):
                await service.create(data, ACTOR_ID)
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

    async def test_publishes_order_created_event(
        self,
        service: OrderService,
        repo: FakeOrderRepository,
        event_publisher: FakeEventPublisher,
        event_stream_publisher: FakeEventStreamPublisher,
    ) -> None:
        repo.allow_create.set()
        data = OrderCreate(restaurant_id=2, total_price=42.50, status="pending")

        order = await service.create(data, ACTOR_ID)

        assert len(event_publisher.published) == 1
        routing_key, payload = event_publisher.published[0]
        assert routing_key == "order.created"
        assert payload["event_type"] == "order.created"
        assert payload["event_version"] == 1
        assert "event_id" in payload
        assert "occurred_at" in payload
        assert payload["data"]["id"] == order.id
        assert payload["data"]["user_id"] == 1
        assert payload["data"]["restaurant_id"] == 2
        assert payload["data"]["status"] == "pending"

        assert len(event_stream_publisher.published) == 1
        topic, key, stream_payload = event_stream_publisher.published[0]
        assert topic == "order.created"
        assert key == str(order.id)
        assert stream_payload == payload

    async def test_no_event_published_when_locked_out(
        self,
        service: OrderService,
        repo: FakeOrderRepository,
        event_publisher: FakeEventPublisher,
        event_stream_publisher: FakeEventStreamPublisher,
    ) -> None:
        data = OrderCreate(restaurant_id=2, total_price=42.50, status="pending")

        first_create = asyncio.create_task(service.create(data, ACTOR_ID))
        try:
            await asyncio.wait_for(repo.create_started.wait(), timeout=1)

            with pytest.raises(DuplicateRequest):
                await service.create(data, ACTOR_ID)
        finally:
            repo.allow_create.set()
        await first_create

        assert len(event_publisher.published) == 1
        assert len(event_stream_publisher.published) == 1


class TestGet:
    async def test_returns_own_order(
        self, service: OrderService, repo: FakeOrderRepository
    ) -> None:
        seeded = repo.seed(an_order(user_id=ACTOR_ID))
        assert await service.get(seeded.id, ACTOR_ID) is seeded

    async def test_raises_not_found_when_missing(self, service: OrderService) -> None:
        with pytest.raises(OrderNotFound):
            await service.get(999, ACTOR_ID)

    async def test_another_users_order_raises_not_found(
        self, service: OrderService, repo: FakeOrderRepository
    ) -> None:
        """OrderNotFound rather than Forbidden, deliberately: the two outcomes
        have to be indistinguishable to the caller, or the endpoint reveals
        which order ids exist."""
        seeded = repo.seed(an_order(user_id=ACTOR_ID))
        with pytest.raises(OrderNotFound):
            await service.get(seeded.id, OTHER_ACTOR_ID)


class TestList:
    async def test_returns_only_the_actors_orders(
        self, service: OrderService, repo: FakeOrderRepository
    ) -> None:
        mine = repo.seed(an_order(user_id=ACTOR_ID))
        theirs = repo.seed(an_order(user_id=OTHER_ACTOR_ID))
        listed = [order.id for order in await service.list(50, 0, ACTOR_ID)]
        assert listed == [mine.id]
        assert theirs.id not in listed


class TestUpdate:
    """update() and delete() enforce ownership by routing through get(), so
    these prove the gate is actually wired up, not just that get() has one."""

    async def test_cannot_update_another_users_order(
        self, service: OrderService, repo: FakeOrderRepository
    ) -> None:
        seeded = repo.seed(an_order(user_id=ACTOR_ID))
        with pytest.raises(OrderNotFound):
            await service.update(
                seeded.id,
                OrderUpdate(total_price=99.99, status="delivered"),
                OTHER_ACTOR_ID,
            )
        assert seeded.total_price == 42.50
        assert seeded.status == "pending"


class TestDelete:
    async def test_cannot_delete_another_users_order(
        self, service: OrderService, repo: FakeOrderRepository
    ) -> None:
        seeded = repo.seed(an_order(user_id=ACTOR_ID))
        with pytest.raises(OrderNotFound):
            await service.delete(seeded.id, OTHER_ACTOR_ID)
        assert await repo.get(seeded.id) is seeded
