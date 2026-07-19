"""Unit tests for OrderNotificationConsumer's idempotency guard."""

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from structlog.testing import capture_logs

from flash.consumers.order_notifications import OrderNotificationConsumer

ORDER_BODY = {"id": 1, "restaurant_id": 2, "total_price": 42.50}


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
