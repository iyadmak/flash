"""
Factory fixtures for v1 API tests.

Data is committed (not just flushed) so that HTTP requests, which run on
separate sessions, can see the inserted rows.

Dependency chain: user → restaurant → order → item
"""

import itertools
import pytest
import pytest_asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from flash.core.security import hash_password, create_access_token
from flash.models import UserModel, RestaurantModel, OrderModel, ItemModel

# ------------------ Instance Factories ------------------
UserFactory = Callable[..., Awaitable[UserModel]]
RestaurantFactory = Callable[..., Awaitable[RestaurantModel]]
OrderFactory = Callable[..., Awaitable[OrderModel]]
ItemFactory = Callable[..., Awaitable[ItemModel]]

_sequence = itertools.count(1)


# ------------------ Construct Factories ------------------
@pytest.fixture
def make_user(async_session: AsyncSession) -> UserFactory:
    async def _make_user(**overrides: Any) -> UserModel:
        n = next(_sequence)
        fields: dict[str, Any] = {
            "username": f"test_user_{n}",
            "email": f"test_user_{n}@example.com",
            "password": "password123",
        }
        fields.update(overrides)
        fields["password"] = hash_password(fields["password"])
        user_instance = UserModel(**fields)
        async_session.add(user_instance)
        await async_session.commit()
        await async_session.refresh(user_instance)
        return user_instance

    return _make_user


@pytest.fixture
def make_restaurant(
    async_session: AsyncSession, make_user: UserFactory
) -> RestaurantFactory:
    async def _make_restaurant(
        owner: UserModel | None = None, **overrides: Any
    ) -> RestaurantModel:
        owner = owner or await make_user()
        fields: dict[str, Any] = {
            "owner_id": owner.id,
            "name": f"{owner.username}'s_test restaurant",
            "address": f"{owner.username}'s Test street",
        }
        fields.update(overrides)
        restaurant_instance = RestaurantModel(**fields)
        async_session.add(restaurant_instance)
        await async_session.commit()
        await async_session.refresh(restaurant_instance)
        return restaurant_instance

    return _make_restaurant


@pytest.fixture
def make_order(
    async_session: AsyncSession,
    make_user: UserFactory,
    make_restaurant: RestaurantFactory,
) -> OrderFactory:
    async def _make_order(
        user: UserModel | None = None,
        restaurant: RestaurantModel | None = None,
        **overrides: Any,
    ) -> OrderModel:
        user = user or await make_user()
        restaurant = restaurant or await make_restaurant()
        fields: dict[str, Any] = {
            "user_id": user.id,
            "restaurant_id": restaurant.id,
            "total_price": 25.99,
            "status": "pending",
        }
        fields.update(overrides)
        order_instance = OrderModel(**fields)
        async_session.add(order_instance)
        await async_session.commit()
        await async_session.refresh(order_instance)
        return order_instance

    return _make_order


@pytest.fixture
def make_item(async_session: AsyncSession, make_order: OrderFactory) -> ItemFactory:
    async def _make_item(
        order: OrderModel | None = None, **overrides: Any
    ) -> ItemModel:
        order = order or await make_order()
        fields: dict[str, Any] = {"order_id": order.id, "name": "Burger", "price": 9.99}
        fields.update(overrides)
        item_instance = ItemModel(**fields)
        async_session.add(item_instance)
        await async_session.commit()
        await async_session.refresh(item_instance)
        return item_instance

    return _make_item


# ------------------ Create instances ------------------
@pytest_asyncio.fixture
async def auth_headers(user: UserModel) -> dict[str, str]:
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user(make_user: UserFactory) -> UserModel:
    return await make_user()


@pytest_asyncio.fixture
async def restaurant(
    make_restaurant: RestaurantFactory, user: UserModel
) -> RestaurantModel:
    return await make_restaurant(owner=user)


@pytest_asyncio.fixture
async def order(
    make_order: OrderFactory, restaurant: RestaurantModel, user: UserModel
) -> OrderModel:
    return await make_order(restaurant=restaurant, user=user)


@pytest_asyncio.fixture
async def item(make_item: ItemFactory, order: OrderModel) -> ItemModel:
    return await make_item(order=order)
