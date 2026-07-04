import structlog
from datetime import datetime
from flash.models.order_model import OrderModel
from flash.schemas.order_schema import OrderCreate, OrderUpdate
from flash.core.exceptions import OrderNotFound
from flash.repositories.order_repository import OrderRepository

logger = structlog.get_logger()


class OrderService:
    def __init__(self, repo: OrderRepository) -> None:
        self._repo = repo

    async def get(self, order_id: int) -> OrderModel:
        order = await self._repo.get(order_id)
        if order is None:
            raise OrderNotFound()
        return order

    async def list(self, limit: int, offset: int) -> list[OrderModel]:
        return list(await self._repo.list(limit, offset))

    async def create(self, data: OrderCreate) -> OrderModel:
        order = OrderModel(
            user_id=data.user_id,
            restaurant_id=data.restaurant_id,
            total_price=data.total_price,
            status=data.status,
        )
        order = await self._repo.create(order)
        await self._repo.commit()
        return order

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
