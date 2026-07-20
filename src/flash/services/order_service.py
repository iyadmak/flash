import structlog
from typing import Protocol, Sequence
from datetime import datetime
from redis.exceptions import LockError
from flash.models.order_model import OrderModel
from flash.schemas.order_schema import (
    OrderCreate,
    OrderUpdate,
    OrderCreatedData,
    OrderCreatedEvent,
)
from flash.core.exceptions import OrderNotFound, DuplicateRequest
from flash.core.adapters.lock import LockProtocol
from flash.core.adapters.events import EventPublisherProtocol

logger = structlog.get_logger()


class OrderRepoProtocol(Protocol):
    async def get(self, id: int) -> OrderModel | None: ...
    async def list(self, limit: int, offset: int) -> Sequence[OrderModel]: ...
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
    ) -> None:
        self._repo = repo
        self._lock_client = lock_client
        self._event_publisher = event_publisher

    async def get(self, order_id: int) -> OrderModel:
        order = await self._repo.get(order_id)
        if order is None:
            raise OrderNotFound()
        return order

    async def list(self, limit: int, offset: int) -> list[OrderModel]:
        return list(await self._repo.list(limit, offset))

    async def create(self, data: OrderCreate) -> OrderModel:
        lock_key = f"order_lock:user:{data.user_id}:restaurant:{data.restaurant_id}"
        try:
            async with self._lock_client.lock(lock_key, timeout=10, blocking=False):
                order = OrderModel(
                    user_id=data.user_id,
                    restaurant_id=data.restaurant_id,
                    total_price=data.total_price,
                    status=data.status,
                )
                order = await self._repo.create(order)
                await self._repo.commit()
                event = OrderCreatedEvent(data=OrderCreatedData.model_validate(order))
                self._event_publisher.publish(
                    "order.created", event.model_dump(mode="json")
                )
                return order
        except LockError:
            raise DuplicateRequest() from None

    async def update(self, order_id: int, data: OrderUpdate) -> OrderModel:
        order = await self.get(order_id)
        old_status = order.status
        order.total_price = data.total_price or order.total_price
        order.status = data.status or order.status
        order.updated_at = datetime.now()
        await self._repo.commit()
        if order.status != old_status:
            logger.info(
                "order_status_changed",
                order_id=order.id,
                old_status=old_status,
                new_status=order.status,
            )
        return order

    async def delete(self, order_id: int) -> None:
        order = await self.get(order_id)
        await self._repo.delete(order)
        await self._repo.commit()
