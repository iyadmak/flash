"""API Dependencies"""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from flash.core.config import Settings, get_settings
from flash.services import UserService, RestaurantService, OrderService, ItemService
from flash.core.db import get_async_session
from flash.repositories.item_repository import ItemRepository


SettingsDep = Annotated[Settings, Depends(get_settings)]
DBSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


def get_item_repository(session: DBSessionDep) -> ItemRepository:
    return ItemRepository(session)


ItemRepoDep = Annotated[ItemRepository, Depends(get_item_repository)]


def get_item_service(repo: ItemRepoDep) -> ItemService:
    return ItemService(repo)


def get_user_service() -> UserService:
    return UserService()


def get_restaurant_service() -> RestaurantService:
    return RestaurantService()


def get_order_service() -> OrderService:
    return OrderService()


ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
RestaurantServiceDep = Annotated[RestaurantService, Depends(get_restaurant_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
