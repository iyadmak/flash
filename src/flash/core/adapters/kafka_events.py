import json
from typing import Any, Protocol
from aiokafka import AIOKafkaProducer


class KafkaEventStreamPublisherProtocol(Protocol):
    async def publish(self, topic: str, key: str, payload: dict[str, Any]) -> None: ...


class KafkaEventStreamPublisher:
    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    async def publish(self, topic: str, key: str, payload: dict[str, Any]) -> None:
        await self._producer.send_and_wait(
            topic,
            value=json.dumps(payload).encode("utf-8"),
            key=key.encode("utf-8"),
        )
