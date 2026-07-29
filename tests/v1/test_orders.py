"""Tests for /api/v1/orders/ CRUD endpoints.

Orders are private to the user who placed them. `auth_headers` authenticates
as the `user` fixture, so `make_order()` with no arguments builds an order
owned by somebody else -- that is the cross-user case throughout.

Money crosses the wire as a JSON string ("42.50"), not a number: pydantic
serializes Decimal that way, because a JSON float cannot hold every 2-decimal
amount exactly. Assertions parse it back to Decimal rather than comparing to a
float literal, so they check the value and not the representation.
"""

from decimal import Decimal

from httpx import AsyncClient

from flash.models.order_model import OrderModel
from flash.models.restaurant_model import RestaurantModel
from flash.models.user_model import UserModel

from .conftest import OrderFactory, UserFactory

BASE = "/api/v1/orders"


class TestListOrders:
    async def test_empty_list(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{BASE}/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_existing_orders(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{BASE}/", headers=auth_headers)
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()]
        assert order.id in ids

    async def test_excludes_other_users_orders(
        self,
        client: AsyncClient,
        order: OrderModel,
        make_order: OrderFactory,
        auth_headers: dict[str, str],
    ) -> None:
        other = await make_order()
        resp = await client.get(f"{BASE}/", headers=auth_headers)
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()]
        assert ids == [order.id]
        assert other.id not in ids


class TestCreateOrder:
    async def test_creates_and_returns_order(
        self,
        client: AsyncClient,
        user: UserModel,
        restaurant: RestaurantModel,
        auth_headers: dict[str, str],
    ) -> None:
        payload = {
            "restaurant_id": restaurant.id,
            "total_price": 42.50,
        }
        resp = await client.post(f"{BASE}/", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        # user_id is never sent -- it comes from the authenticated subject
        assert data["user_id"] == user.id
        assert data["restaurant_id"] == restaurant.id
        assert Decimal(data["total_price"]) == Decimal("42.50")
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_user_id_in_body_cannot_reassign_ownership(
        self,
        client: AsyncClient,
        user: UserModel,
        restaurant: RestaurantModel,
        make_user: UserFactory,
        auth_headers: dict[str, str],
    ) -> None:
        """Regression test for the ownership hole: OrderCreate no longer has a
        user_id field, so pydantic drops it from the body and the order is
        attributed to the token subject regardless of what was sent."""
        victim = await make_user()
        payload = {
            "user_id": victim.id,
            "restaurant_id": restaurant.id,
            "total_price": 42.50,
        }
        resp = await client.post(f"{BASE}/", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["user_id"] == user.id

    async def test_missing_fields_returns_422(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            f"{BASE}/", json={"total_price": 42.50}, headers=auth_headers
        )
        assert resp.status_code == 422

    async def test_nonexistent_restaurant_id_returns_404(
        self,
        client: AsyncClient,
        user: UserModel,
        auth_headers: dict[str, str],
    ) -> None:
        payload = {
            "restaurant_id": 9999,
            "total_price": 42.50,
        }
        resp = await client.post(f"{BASE}/", json=payload, headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["error"] == "restaurant_not_found"


class TestGetOrder:
    async def test_returns_existing_order(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{BASE}/{order.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == order.id
        assert Decimal(data["total_price"]) == order.total_price

    async def test_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{BASE}/9999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_another_users_order_is_indistinguishable_from_missing(
        self,
        client: AsyncClient,
        make_order: OrderFactory,
        auth_headers: dict[str, str],
    ) -> None:
        """404 and not 403 by design -- a 403 would confirm the order exists
        and turn this endpoint into an id-enumeration oracle."""
        other = await make_order()
        resp = await client.get(f"{BASE}/{other.id}", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["error"] == "order_not_found"


class TestChangeOrderStatus:
    """PATCH /{id}/status replaces PUT /{id}. total_price is no longer editable at
    all -- it is about to become derived from the order's items."""

    async def test_advances_the_status(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.patch(
            f"{BASE}/{order.id}/status",
            json={"status": "confirmed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    async def test_illegal_transition_returns_409(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        """pending -> delivered skips the lifecycle. The old PUT allowed it."""
        resp = await client.patch(
            f"{BASE}/{order.id}/status",
            json={"status": "delivered"},
            headers=auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["error"] == "illegal_status_transition"

    async def test_cannot_walk_backwards(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        url = f"{BASE}/{order.id}/status"
        assert (
            await client.patch(url, json={"status": "confirmed"}, headers=auth_headers)
        ).status_code == 200
        resp = await client.patch(url, json={"status": "pending"}, headers=auth_headers)
        assert resp.status_code == 409

    async def test_unknown_status_returns_422(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        """Rejected by the OrderStatus enum on the schema, before any service or
        model code runs -- so it is a validation failure, not a conflict."""
        resp = await client.patch(
            f"{BASE}/{order.id}/status",
            json={"status": "teleported"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_missing_field_returns_422(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.patch(
            f"{BASE}/{order.id}/status", json={}, headers=auth_headers
        )
        assert resp.status_code == 422

    async def test_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.patch(
            f"{BASE}/9999/status",
            json={"status": "confirmed"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_cannot_change_another_users_order(
        self,
        client: AsyncClient,
        make_order: OrderFactory,
        auth_headers: dict[str, str],
    ) -> None:
        other = await make_order()
        resp = await client.patch(
            f"{BASE}/{other.id}/status",
            json={"status": "confirmed"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["error"] == "order_not_found"


class TestDeleteOrder:
    async def test_deletes_order(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.delete(f"{BASE}/{order.id}", headers=auth_headers)
        assert resp.status_code == 204

        resp = await client.get(f"{BASE}/{order.id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.delete(f"{BASE}/9999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_cannot_delete_another_users_order(
        self,
        client: AsyncClient,
        make_order: OrderFactory,
        auth_headers: dict[str, str],
    ) -> None:
        other = await make_order()
        resp = await client.delete(f"{BASE}/{other.id}", headers=auth_headers)
        assert resp.status_code == 404
