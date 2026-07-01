from flash.repositories.restaurant_repository import RestaurantRepository
from flash.core.exceptions import RestaurantNotFound
from flash.schemas.restaurant_schema import (
    RestaurantCreate,
    RestaurantUpdate,
)
from flash.models.restaurant_model import RestaurantModel


class RestaurantService:
    def __init__(self, repo: RestaurantRepository) -> None:
        self._repo = repo

    async def list(self, limit: int, offset: int) -> list[RestaurantModel]:
        return list(await self._repo.list(limit, offset))

    async def get(self, restaurant_id: int) -> RestaurantModel:
        restaurant = await self._repo.get(restaurant_id)
        if restaurant is None:
            raise RestaurantNotFound()
        return restaurant

    async def create(self, data: RestaurantCreate) -> RestaurantModel:
        restaurant = RestaurantModel(
            owner_id=data.owner_id,
            name=data.name,
            address=data.address,
            phone=data.phone,
            email=data.email,
        )
        restaurant = await self._repo.create(restaurant)
        await self._repo.commit()
        return restaurant

    async def update(
        self, restaurant_id: int, data: RestaurantUpdate
    ) -> RestaurantModel:
        restaurant = await self.get(restaurant_id)
        restaurant.name = data.name or restaurant.name
        restaurant.address = data.address or restaurant.address
        restaurant.phone = data.phone or restaurant.phone
        restaurant.email = data.email or restaurant.email
        await self._repo.commit()
        return restaurant

    async def delete(self, restaurant_id: int) -> None:
        restaurant = await self.get(restaurant_id)
        await self._repo.delete(restaurant)
        await self._repo.commit()
