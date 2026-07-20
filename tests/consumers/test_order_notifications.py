"""Unit tests for OrderNotificationConsumer's idempotency guard,
schema validation, and poison-message handling (bounded retries, then
dead-letter)."""

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pydantic
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from structlog.testing import capture_logs

import flash.consumers.order_notifications as order_notifications
from flash.consumers.order_notifications import OrderNotificationConsumer


def make_order_created_body(order_id: int = 1) -> dict[str, Any]:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "order.created",
        "event_version": 1,
        "occurred_at": "2026-07-20T16:00:00Z",
        "data": {
            "id": order_id,
            "user_id": 1,
            "restaurant_id": 2,
            "total_price": 42.50,
            "status": "pending",
            "created_at": "2026-07-20T16:00:00Z",
            "updated_at": "2026-07-20T16:00:00Z",
        },
    }


ORDER_BODY = make_order_created_body()


class FakeMessage:
    def __init__(self, event_id: str | None) -> None:
        self.properties = {"message_id": event_id} if event_id else {}
        self.ack_called = False
        self.reject_calls: list[bool] = []

    def ack(self) -> None:
        self.ack_called = True

    def reject(self, requeue: bool = True) -> None:
        self.reject_calls.append(requeue)


@pytest_asyncio.fixture
async def session_maker(
    async_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(async_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def consumer(
    session_maker: async_sessionmaker[AsyncSession],
) -> OrderNotificationConsumer:
    return OrderNotificationConsumer(connection=None, session_maker=session_maker)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_processed_events(async_engine: AsyncEngine) -> AsyncIterator[None]:
    yield
    async with async_engine.begin() as conn:
        await conn.execute(text("DELETE FROM processed_events"))


async def test_first_delivery_processes_and_records_event(
    consumer: OrderNotificationConsumer,
) -> None:
    with capture_logs() as logs:
        await consumer.handle("event-1", ORDER_BODY)

    events = [log["event"] for log in logs]
    assert "restaurant_notified" in events
    assert "duplicate_event_skipped" not in events

    notified = next(log for log in logs if log["event"] == "restaurant_notified")
    assert notified["order_id"] == ORDER_BODY["data"]["id"]
    assert notified["restaurant_id"] == ORDER_BODY["data"]["restaurant_id"]
    assert notified["total_price"] == ORDER_BODY["data"]["total_price"]


async def test_handle_raises_on_malformed_event(
    consumer: OrderNotificationConsumer,
) -> None:
    malformed_body = {"not": "a valid order.created envelope"}

    with pytest.raises(pydantic.ValidationError):
        await consumer.handle("event-1", malformed_body)


async def test_redelivered_event_id_is_skipped(
    consumer: OrderNotificationConsumer,
) -> None:
    await consumer.handle("event-1", ORDER_BODY)

    with capture_logs() as logs:
        await consumer.handle("event-1", ORDER_BODY)

    events = [log["event"] for log in logs]
    assert events == ["duplicate_event_skipped"]


async def test_different_event_ids_are_both_processed(
    consumer: OrderNotificationConsumer,
) -> None:
    with capture_logs() as logs:
        await consumer.handle("event-1", ORDER_BODY)
        await consumer.handle("event-2", ORDER_BODY)

    events = [log["event"] for log in logs]
    assert events.count("restaurant_notified") == 2


def test_acks_after_recovering_within_retry_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consumer = OrderNotificationConsumer(connection=None, session_maker=None)  # type: ignore[arg-type]
    calls = {"n": 0}

    async def flaky_handle(event_id: str | None, body: dict[str, Any]) -> None:
        calls["n"] += 1
        if calls["n"] < order_notifications.MAX_ATTEMPTS:
            raise ConnectionError("boom")

    monkeypatch.setattr(consumer, "handle", flaky_handle)
    monkeypatch.setattr(
        order_notifications, "time", SimpleNamespace(sleep=lambda _: None)
    )
    message = FakeMessage("event-1")

    consumer.on_order_created(ORDER_BODY, message)

    assert calls["n"] == order_notifications.MAX_ATTEMPTS
    assert message.ack_called is True
    assert message.reject_calls == []


def test_rejects_without_requeue_after_exhausting_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consumer = OrderNotificationConsumer(connection=None, session_maker=None)  # type: ignore[arg-type]

    async def always_fails(event_id: str | None, body: dict[str, Any]) -> None:
        raise ValueError("permanently broken")

    monkeypatch.setattr(consumer, "handle", always_fails)
    monkeypatch.setattr(
        order_notifications, "time", SimpleNamespace(sleep=lambda _: None)
    )
    message = FakeMessage("event-1")

    consumer.on_order_created(ORDER_BODY, message)

    assert message.ack_called is False
    assert message.reject_calls == [False]
