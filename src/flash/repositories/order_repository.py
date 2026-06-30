from sqlalchemy.ext.asyncio import AsyncSession
from flash.repositories.base import BaseRepository
from flash.models.order_model import OrderModel


class OrderRepository(BaseRepository[OrderModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrderModel)
