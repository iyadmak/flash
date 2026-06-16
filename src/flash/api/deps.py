"""API Dependencies"""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from flash.core.config import Settings, get_settings
from flash.services.item_service import ItemService
from flash.services.user_service import UserService
from flash.services.restaurant_service import RestaurantService
from flash.core.db import get_async_session


SettingsDep = Annotated[Settings, Depends(get_settings)]
DBSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


def get_item_service() -> ItemService:
    return ItemService()


def get_user_service() -> UserService:
    return UserService()


def get_restaurant_service() -> RestaurantService:
    return RestaurantService()


ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
RestaurantServiceDep = Annotated[RestaurantService, Depends(get_restaurant_service)]
