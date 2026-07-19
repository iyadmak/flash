from sqlalchemy.ext.asyncio import AsyncSession
from flash.repositories.base import BaseRepository
from flash.models.restaurant_model import RestaurantModel
from flash.core.exceptions import ForeignKeyViolation, UserNotFound


class RestaurantRepository(BaseRepository[RestaurantModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RestaurantModel)

    async def create(self, instance: RestaurantModel) -> RestaurantModel:
        try:
            return await super().create(instance)
        except ForeignKeyViolation as e:
            if e.constraint_name == "fk_restaurants_owner_id_users":
                raise UserNotFound() from None
            raise
