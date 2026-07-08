"""Tests for /api/v1/restaurants/ CRUD endpoints."""

from httpx import AsyncClient

from flash.models.restaurant_model import RestaurantModel
from flash.models.user_model import UserModel

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


class TestCreateRestaurant:
    async def test_creates_and_returns_restaurant(
        self, client: AsyncClient, user: UserModel, auth_headers: dict[str, str]
    ) -> None:
        payload = {"owner_id": user.id, "name": "New Place", "address": "456 Main St"}
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
            "owner_id": user.id,
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

    async def test_missing_name_returns_422(
        self, client: AsyncClient, user: UserModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            f"{BASE}/",
            json={"owner_id": user.id, "address": "123 St"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_missing_address_returns_422(
        self, client: AsyncClient, user: UserModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            f"{BASE}/",
            json={"owner_id": user.id, "name": "No Address"},
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
