"""Tests for /api/v1/restaurants/ CRUD endpoints.

Restaurants are public-read / owner-write. `auth_headers` authenticates as the
`user` fixture and the `restaurant` fixture is owned by that same user, so
`make_restaurant()` with no arguments builds one owned by somebody else.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from flash.models.restaurant_model import RestaurantModel
from flash.models.user_model import UserModel
from .conftest import OrderFactory, RestaurantFactory, UserFactory

BASE = "/api/v1/restaurants"


class TestListRestaurants:
    async def test_empty_list(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{BASE}/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_existing_restaurants(
        self,
        client: AsyncClient,
        restaurant: RestaurantModel,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await client.get(f"{BASE}/", headers=auth_headers)
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()]
        assert restaurant.id in ids

    async def test_includes_restaurants_owned_by_others(
        self,
        client: AsyncClient,
        restaurant: RestaurantModel,
        make_restaurant: RestaurantFactory,
        auth_headers: dict[str, str],
    ) -> None:
        """The deliberate inverse of orders: browsing is the whole point of a
        restaurant listing, so it is never scoped to the caller."""
        theirs = await make_restaurant()
        resp = await client.get(f"{BASE}/", headers=auth_headers)
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()]
        assert {restaurant.id, theirs.id} <= set(ids)


class TestCreateRestaurant:
    async def test_creates_and_returns_restaurant(
        self, client: AsyncClient, user: UserModel, auth_headers: dict[str, str]
    ) -> None:
        payload = {"name": "New Place", "address": "456 Main St"}
        resp = await client.post(f"{BASE}/", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New Place"
        assert data["address"] == "456 Main St"
        assert "id" in data

    async def test_creates_with_optional_fields(
        self, client: AsyncClient, user: UserModel, auth_headers: dict[str, str]
    ) -> None:
        payload = {
            "name": "Full Details",
            "address": "789 Oak Ave",
            "phone": "555-1234",
            "email": "cafe@example.com",
        }
        resp = await client.post(f"{BASE}/", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["phone"] == "555-1234"
        assert data["email"] == "cafe@example.com"

    async def test_owner_is_the_authenticated_user(
        self,
        client: AsyncClient,
        user: UserModel,
        auth_headers: dict[str, str],
        async_session: AsyncSession,
    ) -> None:
        """RestaurantRead does not expose owner_id, so this asserts against the
        row rather than the response body."""
        payload = {"name": "Owned Place", "address": "1 Owner Way"}
        resp = await client.post(f"{BASE}/", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        created = await async_session.get(RestaurantModel, resp.json()["id"])
        assert created is not None
        assert created.owner_id == user.id

    async def test_owner_id_in_body_cannot_reassign_ownership(
        self,
        client: AsyncClient,
        user: UserModel,
        make_user: UserFactory,
        auth_headers: dict[str, str],
        async_session: AsyncSession,
    ) -> None:
        """Regression test for the ownership hole: RestaurantCreate no longer
        has an owner_id field, so pydantic drops it from the body and the
        restaurant is attributed to the token subject regardless."""
        victim = await make_user()
        payload = {
            "owner_id": victim.id,
            "name": "Hijack Attempt",
            "address": "2 Spoof Rd",
        }
        resp = await client.post(f"{BASE}/", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        created = await async_session.get(RestaurantModel, resp.json()["id"])
        assert created is not None
        assert created.owner_id == user.id

    async def test_missing_name_returns_422(
        self, client: AsyncClient, user: UserModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            f"{BASE}/",
            json={"address": "123 St"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_missing_address_returns_422(
        self, client: AsyncClient, user: UserModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            f"{BASE}/",
            json={"name": "No Address"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestGetRestaurant:
    async def test_returns_existing_restaurant(
        self,
        client: AsyncClient,
        restaurant: RestaurantModel,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await client.get(f"{BASE}/{restaurant.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == restaurant.id
        assert data["name"] == restaurant.name

    async def test_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{BASE}/9999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_can_read_another_users_restaurant(
        self,
        client: AsyncClient,
        make_restaurant: RestaurantFactory,
        auth_headers: dict[str, str],
    ) -> None:
        theirs = await make_restaurant()
        resp = await client.get(f"{BASE}/{theirs.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == theirs.id


class TestUpdateRestaurant:
    async def test_updates_name(
        self,
        client: AsyncClient,
        restaurant: RestaurantModel,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await client.put(
            f"{BASE}/{restaurant.id}", json={"name": "Renamed"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

    async def test_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.put(
            f"{BASE}/9999", json={"name": "X"}, headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_cannot_update_another_users_restaurant(
        self,
        client: AsyncClient,
        make_restaurant: RestaurantFactory,
        auth_headers: dict[str, str],
    ) -> None:
        """403 and not 404, unlike orders -- the restaurant is readable by
        anyone, so masking its existence would hide nothing."""
        theirs = await make_restaurant()
        resp = await client.put(
            f"{BASE}/{theirs.id}", json={"name": "Hijacked"}, headers=auth_headers
        )
        assert resp.status_code == 403
        assert resp.json()["error"] == "forbidden"
        assert theirs.name != "Hijacked"


class TestDeleteRestaurant:
    async def test_deletes_restaurant(
        self,
        client: AsyncClient,
        restaurant: RestaurantModel,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await client.delete(f"{BASE}/{restaurant.id}", headers=auth_headers)
        assert resp.status_code == 204

        resp = await client.get(f"{BASE}/{restaurant.id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.delete(f"{BASE}/9999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_cannot_delete_another_users_restaurant(
        self,
        client: AsyncClient,
        make_restaurant: RestaurantFactory,
        auth_headers: dict[str, str],
    ) -> None:
        theirs = await make_restaurant()
        resp = await client.delete(f"{BASE}/{theirs.id}", headers=auth_headers)
        assert resp.status_code == 403

    async def test_conflict_when_orders_reference_it(
        self,
        client: AsyncClient,
        restaurant: RestaurantModel,
        make_order: OrderFactory,
        auth_headers: dict[str, str],
    ) -> None:
        await make_order(restaurant=restaurant)
        resp = await client.delete(f"{BASE}/{restaurant.id}", headers=auth_headers)
        assert resp.status_code == 409
        assert resp.json()["error"] == "delete_conflict"
