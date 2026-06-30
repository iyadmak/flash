from sqlalchemy.ext.asyncio import AsyncSession
from flash.repositories.base import BaseRepository
from flash.models.restaurant_model import RestaurantModel


class RestaurantRepository(BaseRepository[RestaurantModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RestaurantModel)
