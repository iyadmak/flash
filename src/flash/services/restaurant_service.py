from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flash.core.exceptions import RestaurantNotFound
from flash.schemas.restaurant_schema import (
    RestaurantCreate,
    RestaurantUpdate,
)
from flash.models.restaurant_model import RestaurantModel


class RestaurantService:
    async def list(self, session: AsyncSession) -> list[RestaurantModel]:
        restaurants = await session.execute(select(RestaurantModel))
        return list(restaurants.scalars().all())

    async def get(self, session: AsyncSession, restaurant_id: int) -> RestaurantModel:
        restaurant = await session.get(RestaurantModel, restaurant_id)
        if not restaurant:
            raise RestaurantNotFound()
        return restaurant

    async def create(
        self, session: AsyncSession, data: RestaurantCreate
    ) -> RestaurantModel:
        restaurant = RestaurantModel(**data.model_dump())
        session.add(restaurant)
        await session.commit()
        await session.refresh(restaurant)
        return restaurant

    async def update(
        self, session: AsyncSession, restaurant_id: int, data: RestaurantUpdate
    ) -> RestaurantModel:
        restaurant = await self.get(session, restaurant_id)
        if data.name:
            restaurant.name = data.name
        if data.address:
            restaurant.address = data.address
        if data.phone:
            restaurant.phone = data.phone
        if data.email:
            restaurant.email = data.email
        await session.commit()
        await session.refresh(restaurant)
        return restaurant

    async def delete(self, session: AsyncSession, restaurant_id: int) -> None:
        restaurant = await self.get(session, restaurant_id)
        await session.delete(restaurant)
        await session.commit()
