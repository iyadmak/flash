import asyncio
import structlog
from typing import Any
from kombu import Connection, Queue
from kombu.mixins import ConsumerMixin
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from flash.core.adapters.events import domain_events_exchange
from flash.core.config import get_settings
from flash.core.consumer_db import consumer_session_maker
from flash.core.exceptions import UniqueConstraintViolation
from flash.models.processed_event_model import ProcessedEventModel
from flash.repositories.processed_event_repository import ProcessedEventRepository

logger = structlog.get_logger()

CONSUMER_NAME = "order_notifications"

order_notifications_queue = Queue(
    "flash.order_notifications",
    exchange=domain_events_exchange,
    routing_key="order.created",
    durable=True,
)


class OrderNotificationConsumer(ConsumerMixin):  # type: ignore[misc]
    def __init__(
        self,
        connection: Connection,
        session_maker: async_sessionmaker[AsyncSession] = consumer_session_maker,
    ) -> None:
        self.connection = connection
        self._session_maker = session_maker

    def get_consumers(self, Consumer: Any, channel: Any) -> list[Any]:
        return [
            Consumer(
                queues=[order_notifications_queue],
                callbacks=[self.on_order_created],
                accept=["json"],
            )
        ]

    def on_order_created(self, body: dict[str, Any], message: Any) -> None:
        event_id = message.properties.get("message_id")
        try:
            asyncio.run(self.handle(event_id, body))
        finally:
            message.ack()

    async def handle(self, event_id: str | None, body: dict[str, Any]) -> None:
        async with self._session_maker() as session:
            repo = ProcessedEventRepository(session)
            try:
                await repo.create(
                    ProcessedEventModel(consumer_name=CONSUMER_NAME, event_id=event_id)
                )
                await repo.commit()
            except UniqueConstraintViolation:
                logger.info("duplicate_event_skipped", event_id=event_id)
                return
        logger.info(
            "restaurant_notified",
            order_id=body.get("id"),
            restaurant_id=body.get("restaurant_id"),
            total_price=body.get("total_price"),
        )


def main() -> None:
    with Connection(get_settings().rabbitmq_url) as connection:
        OrderNotificationConsumer(connection).run()


if __name__ == "__main__":
    main()
