"""
Factory fixtures for v1 API tests.

Data is committed (not just flushed) so that HTTP requests, which run on
separate sessions, can see the inserted rows.

Dependency chain: user → restaurant → order → item
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from flash.core.security import hash_password
from flash.models.item_model import ItemModel
from flash.models.order_model import OrderModel
from flash.models.restaurant_model import RestaurantModel
from flash.models.user_model import UserModel


@pytest_asyncio.fixture
async def user(async_session: AsyncSession) -> UserModel:
    model = UserModel(
        username="testuser",
        email="test@example.com",
        password=hash_password("password123"),
    )
    async_session.add(model)
    await async_session.commit()
    await async_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def restaurant(async_session: AsyncSession, user: UserModel) -> RestaurantModel:
    model = RestaurantModel(
        owner_id=user.id,
        name="Test Restaurant",
        address="123 Test Street",
    )
    async_session.add(model)
    await async_session.commit()
    await async_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def order(
    async_session: AsyncSession, user: UserModel, restaurant: RestaurantModel
) -> OrderModel:
    model = OrderModel(
        user_id=user.id,
        restaurant_id=restaurant.id,
        total_price=25.99,
        status="pending",
    )
    async_session.add(model)
    await async_session.commit()
    await async_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def item(async_session: AsyncSession, order: OrderModel) -> ItemModel:
    model = ItemModel(
        order_id=order.id,
        name="Burger",
        price=9.99,
    )
    async_session.add(model)
    await async_session.commit()
    await async_session.refresh(model)
    return model
