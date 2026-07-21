import asyncio
import structlog
from collections.abc import Awaitable
from typing import Protocol
import redis.asyncio as redis
from aiokafka import AIOKafkaConsumer
from flash.core.config import get_settings
from flash.schemas.order_schema import OrderCreatedEvent

logger = structlog.get_logger()

CONSUMER_GROUP = "flash-analytics"
TOPIC = "order.created"


class MetricsRedisProtocol(Protocol):
    def incr(self, name: str) -> Awaitable[int]: ...
    def incrby(self, name: str, amount: int) -> Awaitable[int]: ...


def _order_count_key(restaurant_id: int) -> str:
    return f"metrics:restaurant:{restaurant_id}:order_count"


def _revenue_cents_key(restaurant_id: int) -> str:
    return f"metrics:restaurant:{restaurant_id}:revenue_cents"


async def handle(redis_client: MetricsRedisProtocol, event: OrderCreatedEvent) -> None:
    revenue_cents = round(event.data.total_price * 100)
    await redis_client.incr(_order_count_key(event.data.restaurant_id))
    await redis_client.incrby(
        (_revenue_cents_key(event.data.restaurant_id)), revenue_cents
    )


async def main() -> None:
    settings = get_settings()
    redis_client = redis.Redis.from_url(settings.redis_url)
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=CONSUMER_GROUP,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for message in consumer:
            try:
                event = OrderCreatedEvent.model_validate_json(message.value)
                await handle(redis_client, event)
            except Exception:
                logger.error(
                    "order_metrics_update_failed",
                    offset=message.offset,
                    partition=message.partition,
                    exc_info=True,
                )
            else:
                logger.info(
                    "order_metrics_updated",
                    restaurant_id=event.data.restaurant_id,
                    order_id=event.data.id,
                )
            await consumer.commit()
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())
