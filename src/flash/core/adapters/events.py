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
        # Pooled producer/connection, not a single shared Producer(self._connection):
        # this is called from multiple threads at once (via asyncio.to_thread in
        # OrderService.create), and kombu Connection/Channel objects aren't safe for
        # concurrent multi-threaded use. The pool hands each caller its own
        # connection instead of everyone contending on one.
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
