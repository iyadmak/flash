"""Tests for /api/v1/orders/ CRUD endpoints."""

from httpx import AsyncClient

from flash.models.order_model import OrderModel
from flash.models.restaurant_model import RestaurantModel
from flash.models.user_model import UserModel

BASE = "/api/v1/orders"


class TestListOrders:
    async def test_empty_list(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_existing_orders(
        self, client: AsyncClient, order: OrderModel
    ) -> None:
        resp = await client.get(f"{BASE}/")
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()]
        assert order.id in ids


class TestCreateOrder:
    async def test_creates_and_returns_order(
        self,
        client: AsyncClient,
        user: UserModel,
        restaurant: RestaurantModel,
    ) -> None:
        payload = {
            "user_id": user.id,
            "restaurant_id": restaurant.id,
            "total_price": 42.50,
            "status": "pending",
        }
        resp = await client.post(f"{BASE}/", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] == user.id
        assert data["restaurant_id"] == restaurant.id
        assert data["total_price"] == 42.50
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_missing_fields_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(f"{BASE}/", json={"status": "pending"})
        assert resp.status_code == 422


class TestGetOrder:
    async def test_returns_existing_order(
        self, client: AsyncClient, order: OrderModel
    ) -> None:
        resp = await client.get(f"{BASE}/{order.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == order.id
        assert data["total_price"] == order.total_price

    async def test_not_found(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/9999")
        assert resp.status_code == 404


class TestUpdateOrder:
    async def test_updates_price_and_status(
        self, client: AsyncClient, order: OrderModel
    ) -> None:
        # OrderUpdate requires both fields (neither is Optional)
        resp = await client.put(
            f"{BASE}/{order.id}",
            json={"total_price": 99.99, "status": "delivered"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_price"] == 99.99
        assert data["status"] == "delivered"

    async def test_missing_field_returns_422(
        self, client: AsyncClient, order: OrderModel
    ) -> None:
        resp = await client.put(f"{BASE}/{order.id}", json={"total_price": 10.0})
        assert resp.status_code == 422

    async def test_not_found(self, client: AsyncClient) -> None:
        resp = await client.put(
            f"{BASE}/9999", json={"total_price": 10.0, "status": "pending"}
        )
        assert resp.status_code == 404


class TestDeleteOrder:
    async def test_deletes_order(self, client: AsyncClient, order: OrderModel) -> None:
        resp = await client.delete(f"{BASE}/{order.id}")
        assert resp.status_code == 204

        resp = await client.get(f"{BASE}/{order.id}")
        assert resp.status_code == 404

    async def test_not_found(self, client: AsyncClient) -> None:
        resp = await client.delete(f"{BASE}/9999")
        assert resp.status_code == 404
