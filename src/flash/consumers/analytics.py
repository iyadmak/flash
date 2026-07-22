import asyncio
import structlog
import redis.asyncio as redis
from collections.abc import Awaitable
from typing import Protocol, Any
from aiokafka import AIOKafkaConsumer
from flash.core.config import get_settings
from flash.schemas.order_schema import OrderCreatedEvent
from flash.core.adapters.mongodb import ANALYTICS_DB_NAME, get_mongo_client

logger = structlog.get_logger()

CONSUMER_GROUP = "flash-analytics"
TOPIC = "order.created"


class MetricsRedisProtocol(Protocol):
    def incr(self, name: str) -> Awaitable[int]: ...
    def incrby(self, name: str, amount: int) -> Awaitable[int]: ...


class ReportsCollectionProtocol(Protocol):
    def replace_one(
        self, filter: dict[str, Any], replacement: dict[str, Any], upsert: bool = False
    ) -> Awaitable[Any]: ...


class DailyReportCollectionProtocol(Protocol):
    def update_one(
        self, filter: dict[str, Any], update: dict[str, Any], upsert: bool = False
    ) -> Awaitable[Any]: ...


def _order_count_key(restaurant_id: int) -> str:
    return f"metrics:restaurant:{restaurant_id}:order_count"


def _revenue_cents_key(restaurant_id: int) -> str:
    return f"metrics:restaurant:{restaurant_id}:revenue_cents"


def _daily_report_id(restaurant_id: int, report_date: str) -> str:
    return f"{restaurant_id}:{report_date}"


async def handle(
    redis_client: MetricsRedisProtocol,
    reports_collection: ReportsCollectionProtocol,
    daily_reports_collection: DailyReportCollectionProtocol,
    event: OrderCreatedEvent,
) -> None:
    revenue_cents = round(event.data.total_price * 100)
    await redis_client.incr(_order_count_key(event.data.restaurant_id))
    await redis_client.incrby(
        (_revenue_cents_key(event.data.restaurant_id)), revenue_cents
    )
    report = event.model_dump(mode="json")
    report["_id"] = report["event_id"]
    result = await reports_collection.replace_one(
        {"_id": report["_id"]}, report, upsert=True
    )

    if result.upserted_id is not None:
        report_date = event.data.created_at.date().isoformat()
        await daily_reports_collection.update_one(
            {"_id": _daily_report_id(event.data.restaurant_id, report_date)},
            {
                "$inc": {"order_count": 1, "revenue_cents": revenue_cents},
                "$setOnInsert": {
                    "restaurant_id": event.data.restaurant_id,
                    "report_date": report_date,
                },
            },
            upsert=True,
        )


async def main() -> None:
    settings = get_settings()
    redis_client = redis.Redis.from_url(settings.redis_url)
    mongodb_client = get_mongo_client()
    reports_collection = mongodb_client.get_database(ANALYTICS_DB_NAME).get_collection(
        "reports"
    )
    daily_reports_collection = mongodb_client.get_database(
        ANALYTICS_DB_NAME
    ).get_collection("restaurant_daily_reports")
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
                await handle(
                    redis_client, reports_collection, daily_reports_collection, event
                )
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
