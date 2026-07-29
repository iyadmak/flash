import uuid
from functools import lru_cache
from typing import Any, Protocol
from kombu import Connection, Exchange
from kombu.pools import producers

from flash.core.config import get_settings

domain_events_exchange = Exchange("flash.events", type="topic", durable=True)
domain_events_dlx = Exchange("flash.domain_events.dlx", type="direct", durable=True)


class EventPublisherProtocol(Protocol):
    def publish(self, routing_key: str, payload: dict[str, Any]) -> None: ...


class KombuEventPublisher:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        # Pooled, not one shared Producer: called from several threads at once via
        # asyncio.to_thread, and kombu channels are not thread-safe.
        with producers[self._connection].acquire(block=True) as producer:
            producer.publish(
                payload,
                exchange=domain_events_exchange,
                routing_key=routing_key,
                declare=[domain_events_exchange],
                serializer="json",
                message_id=str(uuid.uuid4()),
            )


@lru_cache
def get_event_publisher() -> EventPublisherProtocol:
    """Domain-event publisher: real rabbitmq in the app. Overriden to a fake in tests."""
    return KombuEventPublisher(connection=Connection(get_settings().rabbitmq_url))
