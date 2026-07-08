"""Tests for /api/v1/items/ CRUD endpoints."""

from httpx import AsyncClient

from flash.models.item_model import ItemModel
from flash.models.order_model import OrderModel
from .conftest import ItemFactory

BASE = "/api/v1/items"


class TestListItems:
    async def test_empty_list(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{BASE}/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"items": [], "next_cursor": None}

    async def test_returns_existing_items(
        self, client: AsyncClient, item: ItemModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{BASE}/", headers=auth_headers)
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert item.id in ids

    async def test_paginates_with_cursor(
        self, client: AsyncClient, make_item: ItemFactory, auth_headers: dict[str, str]
    ) -> None:
        items = [await make_item() for _ in range(5)]
        ids = sorted(i.id for i in items)

        page1 = await client.get(f"{BASE}/", params={"limit": 2}, headers=auth_headers)
        data1 = page1.json()
        assert [i["id"] for i in data1["items"]] == ids[:2]
        assert data1["next_cursor"] is not None

        page2 = await client.get(
            f"{BASE}/",
            params={"limit": 2, "cursor": data1["next_cursor"]},
            headers=auth_headers,
        )
        data2 = page2.json()
        assert [i["id"] for i in data2["items"]] == ids[2:4]
        assert data2["next_cursor"] is not None

        page3 = await client.get(
            f"{BASE}/",
            params={"limit": 2, "cursor": data2["next_cursor"]},
            headers=auth_headers,
        )
        data3 = page3.json()
        assert [i["id"] for i in data3["items"]] == ids[4:5]
        assert data3["next_cursor"] is None


class TestGetItem:
    async def test_returns_existing_item(
        self, client: AsyncClient, item: ItemModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{BASE}/{item.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == item.id
        assert data["name"] == item.name
        assert data["price"] == item.price
        assert data["order_id"] == item.order_id

    async def test_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{BASE}/9999", headers=auth_headers)
        assert resp.status_code == 404


class TestCreateItem:
    async def test_creates_and_returns_item(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        payload = {"name": "Pizza", "price": 12.50, "order_id": order.id}
        resp = await client.post(f"{BASE}/", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Pizza"
        assert data["price"] == 12.50
        assert data["order_id"] == order.id
        assert "id" in data

    async def test_missing_required_field_returns_422(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # price and order_id are required
        resp = await client.post(
            f"{BASE}/", json={"name": "Pizza"}, headers=auth_headers
        )
        assert resp.status_code == 422


class TestUpdateItem:
    async def test_updates_name(
        self, client: AsyncClient, item: ItemModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.patch(
            f"{BASE}/{item.id}", json={"name": "Salad"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Salad"

    async def test_patch_preserves_unchanged_fields(
        self, client: AsyncClient, item: ItemModel, auth_headers: dict[str, str]
    ) -> None:
        # PATCH only name — price must be unchanged
        resp = await client.patch(
            f"{BASE}/{item.id}", json={"name": "Wrap"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["price"] == item.price

    async def test_updates_price(
        self, client: AsyncClient, item: ItemModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.patch(
            f"{BASE}/{item.id}", json={"price": 19.99}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["price"] == 19.99

    async def test_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.patch(
            f"{BASE}/9999", json={"name": "X"}, headers=auth_headers
        )
        assert resp.status_code == 404


class TestDeleteItem:
    async def test_deletes_item(
        self, client: AsyncClient, item: ItemModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.delete(f"{BASE}/{item.id}", headers=auth_headers)
        assert resp.status_code == 204

        resp = await client.get(f"{BASE}/{item.id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.delete(f"{BASE}/9999", headers=auth_headers)
        assert resp.status_code == 404
