from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flash.models.order_model import OrderModel
from flash.schemas.order_schema import OrderCreate, OrderUpdate
from flash.core.exceptions import OrderNotFound


class OrderService:
    async def list(self, session: AsyncSession) -> list[OrderModel]:
        orders = await session.execute(select(OrderModel))
        return list(orders.scalars().all())

    async def get(self, session: AsyncSession, order_id: int) -> OrderModel:
        order = await session.get(OrderModel, order_id)
        if not order:
            raise OrderNotFound()
        return order

    async def create(self, session: AsyncSession, data: OrderCreate) -> OrderModel:
        order = OrderModel(
            user_id=data.user_id,
            restaurant_id=data.restaurant_id,
            total_price=data.total_price,
            status=data.status,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order

    async def update(
        self, session: AsyncSession, order_id: int, data: OrderUpdate
    ) -> OrderModel:
        order = await self.get(session, order_id)
        if data.total_price:
            order.total_price = data.total_price
        if data.status:
            order.status = data.status
        await session.commit()
        await session.refresh(order)
        return order

    async def delete(self, session: AsyncSession, order_id: int) -> None:
        order = await self.get(session, order_id)
        await session.delete(order)
        await session.commit()
