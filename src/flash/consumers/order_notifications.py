import structlog
from typing import Any
from kombu import Connection, Queue
from kombu.mixins import ConsumerMixin
from flash.core.adapters.events import domain_events_exchange
from flash.core.config import get_settings

logger = structlog.get_logger()

order_notifications_queue = Queue(
    "flash.order_notifications",
    exchange=domain_events_exchange,
    routing_key="order.created",
    durable=True,
)


class OrderNotificationConsumer(ConsumerMixin):  # type: ignore[misc]
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def get_consumers(self, Consumer: Any, channel: Any) -> list[Any]:
        return [
            Consumer(
                queues=[order_notifications_queue],
                callbacks=[self.on_order_created],
                accept=["json"],
            )
        ]

    def on_order_created(self, body: dict[str, Any], message: Any) -> None:
        try:
            logger.info(
                "restaurant_notified",
                order_id=body.get("id"),
                restaurant_id=body.get("restaurant_id"),
                total_price=body.get("total_price"),
            )
        finally:
            message.ack()


def main() -> None:
    with Connection(get_settings().rabbitmq_url) as connection:
        OrderNotificationConsumer(connection).run()


if __name__ == "__main__":
    main()
