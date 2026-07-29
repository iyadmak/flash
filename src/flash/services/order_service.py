import asyncio
import structlog
from typing import Protocol, Sequence
from redis.exceptions import LockError
from flash.domain.order_status import OrderStatus
from flash.models.order_model import OrderModel
from flash.schemas.order_schema import (
    OrderCreate,
    OrderCreatedData,
    OrderCreatedEvent,
)
from flash.core.exceptions import OrderNotFound, DuplicateRequest
from flash.core.adapters.lock import LockProtocol
from flash.core.adapters.events import EventPublisherProtocol
from flash.core.adapters.kafka_events import KafkaEventStreamPublisherProtocol

logger = structlog.get_logger()


class OrderRepoProtocol(Protocol):
    async def get(self, entity_id: int) -> OrderModel | None: ...
    async def list_for_user(
        self, user_id: int, limit: int, offset: int
    ) -> Sequence[OrderModel]: ...
    async def create(self, instance: OrderModel) -> OrderModel: ...
    async def delete(self, instance: OrderModel) -> None: ...
    async def commit(self) -> None: ...
    async def refresh(self, instance: OrderModel) -> None: ...


class OrderService:
    def __init__(
        self,
        repo: OrderRepoProtocol,
        lock_client: LockProtocol,
        event_publisher: EventPublisherProtocol,
        event_stream_publisher: KafkaEventStreamPublisherProtocol,
    ) -> None:
        self._repo = repo
        self._lock_client = lock_client
        self._event_publisher = event_publisher
        self._event_stream_publisher = event_stream_publisher

    async def get(self, order_id: int, actor_id: int) -> OrderModel:
        order = await self._repo.get(order_id)
        if order is None:
            raise OrderNotFound()
        if order.user_id != actor_id:
            # 404, not 403: a 403 would confirm the order exists. Logged so the two
            # cases stay distinguishable to us, not to the caller.
            logger.warning("order_access_denied", order_id=order_id, actor_id=actor_id)
            raise OrderNotFound()
        return order

    async def list(self, limit: int, offset: int, actor_id: int) -> list[OrderModel]:
        return list(await self._repo.list_for_user(actor_id, limit, offset))

    async def create(self, data: OrderCreate, actor_id: int) -> OrderModel:
        lock_key = f"order_lock:user:{actor_id}:restaurant:{data.restaurant_id}"
        try:
            async with self._lock_client.lock(lock_key, timeout=10, blocking=False):
                # Always PENDING: the client cannot pick a starting state.
                order = OrderModel(
                    user_id=actor_id,
                    restaurant_id=data.restaurant_id,
                    total_price=data.total_price,
                    status=OrderStatus.PENDING,
                )
                order = await self._repo.create(order)
                await self._repo.commit()
                event = OrderCreatedEvent(data=OrderCreatedData.model_validate(order))
                payload = event.model_dump(mode="json")
                await asyncio.gather(
                    asyncio.to_thread(
                        self._event_publisher.publish, "order.created", payload
                    ),
                    self._event_stream_publisher.publish(
                        topic="order.created", key=str(order.id), payload=payload
                    ),
                )
                return order
        except LockError:
            raise DuplicateRequest() from None

    async def change_status(
        self, order_id: int, new_status: OrderStatus, actor_id: int
    ) -> OrderModel:
        """Orchestration only; the transition rule lives on the model."""
        order = await self.get(order_id, actor_id)
        old_status = order.status
        order.change_status(new_status)
        await self._repo.commit()
        # updated_at is server-side, so the in-memory copy is stale after commit.
        await self._repo.refresh(order)
        logger.info(
            "order_status_changed",
            order_id=order.id,
            old_status=old_status,
            new_status=order.status,
        )
        return order

    async def delete(self, order_id: int, actor_id: int) -> None:
        order = await self.get(order_id, actor_id)
        await self._repo.delete(order)
        await self._repo.commit()
