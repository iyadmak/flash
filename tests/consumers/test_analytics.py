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
    await handle(redis_client, make_event(restaurant_id=5, total_price=12.50))

    assert redis_client.counters["metrics:restaurant:5:order_count"] == 1
    assert redis_client.counters["metrics:restaurant:5:revenue_cents"] == 1250


async def test_accumulates_across_multiple_orders() -> None:
    redis_client = FakeMetricsRedis()
    await handle(redis_client, make_event(restaurant_id=5, total_price=10.00))
    await handle(redis_client, make_event(restaurant_id=5, total_price=5.00))

    assert redis_client.counters["metrics:restaurant:5:order_count"] == 2
    assert redis_client.counters["metrics:restaurant:5:revenue_cents"] == 1500


async def test_different_restaurants_tracked_separately() -> None:
    redis_client = FakeMetricsRedis()
    await handle(redis_client, make_event(restaurant_id=5, total_price=10.00))
    await handle(redis_client, make_event(restaurant_id=6, total_price=20.00))

    assert redis_client.counters["metrics:restaurant:5:order_count"] == 1
    assert redis_client.counters["metrics:restaurant:6:order_count"] == 1
