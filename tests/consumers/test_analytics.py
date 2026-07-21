from typing import Any

from flash.consumers.analytics import handle
from flash.schemas.order_schema import OrderCreatedData, OrderCreatedEvent


class FakeMetricsRedis:
    def __init__(self) -> None:
        self.counters: dict[str, float] = {}

    async def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return int(self.counters[key])

    async def incrby(self, key: str, amount: int) -> int:
        self.counters[key] = self.counters.get(key, 0) + amount
        return int(self.counters[key])


class FakeReportsCollection:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}

    async def replace_one(
        self, filter: dict[str, Any], replacement: dict[str, Any], upsert: bool = False
    ) -> None:
        self.documents[filter["_id"]] = replacement


def make_event(restaurant_id: int, total_price: float) -> OrderCreatedEvent:
    return OrderCreatedEvent(
        data=OrderCreatedData(
            id=1,
            user_id=1,
            restaurant_id=restaurant_id,
            total_price=total_price,
            status="pending",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
    )


async def test_increments_order_count_and_revenue_cents() -> None:
    redis_client = FakeMetricsRedis()
    reports = FakeReportsCollection()
    await handle(redis_client, reports, make_event(restaurant_id=5, total_price=12.50))

    assert redis_client.counters["metrics:restaurant:5:order_count"] == 1
    assert redis_client.counters["metrics:restaurant:5:revenue_cents"] == 1250


async def test_accumulates_across_multiple_orders() -> None:
    redis_client = FakeMetricsRedis()
    reports = FakeReportsCollection()
    await handle(redis_client, reports, make_event(restaurant_id=5, total_price=10.00))
    await handle(redis_client, reports, make_event(restaurant_id=5, total_price=5.00))

    assert redis_client.counters["metrics:restaurant:5:order_count"] == 2
    assert redis_client.counters["metrics:restaurant:5:revenue_cents"] == 1500


async def test_different_restaurants_tracked_separately() -> None:
    redis_client = FakeMetricsRedis()
    reports = FakeReportsCollection()
    await handle(redis_client, reports, make_event(restaurant_id=5, total_price=10.00))
    await handle(redis_client, reports, make_event(restaurant_id=6, total_price=20.00))

    assert redis_client.counters["metrics:restaurant:5:order_count"] == 1
    assert redis_client.counters["metrics:restaurant:6:order_count"] == 1


async def test_report_document_is_stored_with_event_id_as_mongo_id() -> None:
    redis_client = FakeMetricsRedis()
    reports = FakeReportsCollection()
    event = make_event(restaurant_id=5, total_price=10.00)

    await handle(redis_client, reports, event)

    stored = reports.documents[str(event.event_id)]
    assert stored["data"]["restaurant_id"] == 5
    assert stored["data"]["total_price"] == 10.00


async def test_replaying_same_event_id_does_not_duplicate_report() -> None:
    redis_client = FakeMetricsRedis()
    reports = FakeReportsCollection()
    event = make_event(restaurant_id=5, total_price=10.00)

    await handle(redis_client, reports, event)
    await handle(redis_client, reports, event)  # simulates redelivery of the same event

    assert len(reports.documents) == 1
    assert reports.documents[str(event.event_id)]["data"]["restaurant_id"] == 5
