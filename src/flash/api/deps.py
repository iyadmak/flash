"""API Dependencies"""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from flash.core.config import Settings, get_settings
from flash.services import (
    UserService,
    RestaurantService,
    OrderService,
    ItemService,
    AuthService,
)
from flash.core.db import get_async_session
from flash.repositories import (
    ItemRepository,
    OrderRepository,
    RestaurantRepository,
    UserRepository,
)

# ------------------- General dependencies -------------------
SettingsDep = Annotated[Settings, Depends(get_settings)]
DBSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


# ------------------- Repository dependencies -------------------
def get_item_repository(session: DBSessionDep) -> ItemRepository:
    return ItemRepository(session)


def get_order_repository(session: DBSessionDep) -> OrderRepository:
    return OrderRepository(session)


def get_restaurant_repository(session: DBSessionDep) -> RestaurantRepository:
    return RestaurantRepository(session)


def get_user_repository(session: DBSessionDep) -> UserRepository:
    return UserRepository(session)


ItemRepoDep = Annotated[ItemRepository, Depends(get_item_repository)]
OrderRepoDep = Annotated[OrderRepository, Depends(get_order_repository)]
RestaurantRepoDep = Annotated[RestaurantRepository, Depends(get_restaurant_repository)]
UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]


# ------------------- Service dependencies -------------------
def get_auth_service(repo: UserRepoDep) -> AuthService:
    return AuthService(repo)


def get_item_service(repo: ItemRepoDep) -> ItemService:
    return ItemService(repo)


def get_user_service(repo: UserRepoDep) -> UserService:
    return UserService(repo)


def get_restaurant_service(repo: RestaurantRepoDep) -> RestaurantService:
    return RestaurantService(repo)


def get_order_service(repo: OrderRepoDep) -> OrderService:
    return OrderService(repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
RestaurantServiceDep = Annotated[RestaurantService, Depends(get_restaurant_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
