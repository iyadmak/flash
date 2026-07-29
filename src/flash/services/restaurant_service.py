from collections.abc import Sequence
from typing import Protocol

from flash.core.exceptions import Forbidden, RestaurantNotFound
from flash.schemas.restaurant_schema import (
    RestaurantCreate,
    RestaurantUpdate,
)
from flash.models.restaurant_model import RestaurantModel


class RestaurantRepoProtocol(Protocol):
    async def get(self, entity_id: int) -> RestaurantModel | None: ...
    async def list(self, limit: int, offset: int) -> Sequence[RestaurantModel]: ...
    async def create(self, instance: RestaurantModel) -> RestaurantModel: ...
    async def delete(self, instance: RestaurantModel) -> None: ...
    async def commit(self) -> None: ...


class RestaurantService:
    def __init__(self, repo: RestaurantRepoProtocol) -> None:
        self._repo = repo

    async def list(self, limit: int, offset: int) -> list[RestaurantModel]:
        return list(await self._repo.list(limit, offset))

    async def get(self, restaurant_id: int) -> RestaurantModel:
        restaurant = await self._repo.get(restaurant_id)
        if restaurant is None:
            raise RestaurantNotFound()
        return restaurant

    async def create(self, data: RestaurantCreate, actor_id: int) -> RestaurantModel:
        restaurant = RestaurantModel(
            owner_id=actor_id,
            name=data.name,
            address=data.address,
            phone=data.phone,
            email=data.email,
        )
        restaurant = await self._repo.create(restaurant)
        await self._repo.commit()
        return restaurant

    async def _get_owned(self, restaurant_id: int, actor_id: int) -> RestaurantModel:
        """Resolve a restaurant the actor may write to.

        Existence first, so a missing one is a 404 and somebody else's is a 403 --
        anyone may read a restaurant, so hiding its existence would buy nothing.
        """
        restaurant = await self.get(restaurant_id)
        if restaurant.owner_id != actor_id:
            raise Forbidden()
        return restaurant

    async def update(
        self, restaurant_id: int, data: RestaurantUpdate, actor_id: int
    ) -> RestaurantModel:
        restaurant = await self._get_owned(restaurant_id, actor_id)
        # `is not None`, not `or`: an empty string is a real value.
        if data.name is not None:
            restaurant.name = data.name
        if data.address is not None:
            restaurant.address = data.address
        if data.phone is not None:
            restaurant.phone = data.phone
        if data.email is not None:
            restaurant.email = data.email
        await self._repo.commit()
        return restaurant

    async def delete(self, restaurant_id: int, actor_id: int) -> None:
        restaurant = await self._get_owned(restaurant_id, actor_id)
        await self._repo.delete(restaurant)
        await self._repo.commit()
