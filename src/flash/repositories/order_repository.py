from sqlalchemy.ext.asyncio import AsyncSession
from flash.repositories.base import BaseRepository
from flash.models.order_model import OrderModel
from flash.core.exceptions import ForeignKeyViolation, RestaurantNotFound, UserNotFound


class OrderRepository(BaseRepository[OrderModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrderModel)

    async def create(self, instance: OrderModel) -> OrderModel:
        try:
            return await super().create(instance)
        except ForeignKeyViolation as e:
            if e.constraint_name == "fk_orders_restaurant_id_restaurants":
                raise RestaurantNotFound() from None
            if e.constraint_name == "fk_orders_user_id_users":
                raise UserNotFound() from None
            raise
