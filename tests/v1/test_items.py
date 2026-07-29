"""Tests for /api/v1/orders/{order_id}/items/ — items as a subresource.

`auth_headers` authenticates as the `user` fixture and the `order` fixture
belongs to that user, so `make_order()` with no arguments builds an order owned
by somebody else.
"""

from httpx import AsyncClient

from flash.models.item_model import ItemModel
from flash.models.order_model import OrderModel
from flash.models.user_model import UserModel
from .conftest import ItemFactory, OrderFactory


def items_url(order_id: int) -> str:
    return f"/api/v1/orders/{order_id}/items"


class TestListItems:
    async def test_empty_list(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{items_url(order.id)}/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"items": [], "next_cursor": None}

    async def test_returns_existing_items(
        self,
        client: AsyncClient,
        order: OrderModel,
        item: ItemModel,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await client.get(f"{items_url(order.id)}/", headers=auth_headers)
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert item.id in ids

    async def test_excludes_items_from_other_orders(
        self,
        client: AsyncClient,
        order: OrderModel,
        item: ItemModel,
        make_item: ItemFactory,
        auth_headers: dict[str, str],
    ) -> None:
        elsewhere = await make_item()
        resp = await client.get(f"{items_url(order.id)}/", headers=auth_headers)
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert ids == [item.id]
        assert elsewhere.id not in ids

    async def test_another_users_order_returns_404(
        self,
        client: AsyncClient,
        make_order: OrderFactory,
        auth_headers: dict[str, str],
    ) -> None:
        theirs = await make_order()
        resp = await client.get(f"{items_url(theirs.id)}/", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["error"] == "order_not_found"

    async def test_paginates_with_cursor(
        self,
        client: AsyncClient,
        order: OrderModel,
        make_item: ItemFactory,
        auth_headers: dict[str, str],
    ) -> None:
        items = [await make_item(order=order) for _ in range(5)]
        ids = sorted(i.id for i in items)
        url = f"{items_url(order.id)}/"

        page1 = await client.get(url, params={"limit": 2}, headers=auth_headers)
        data1 = page1.json()
        assert [i["id"] for i in data1["items"]] == ids[:2]
        assert data1["next_cursor"] is not None

        page2 = await client.get(
            url,
            params={"limit": 2, "cursor": data1["next_cursor"]},
            headers=auth_headers,
        )
        data2 = page2.json()
        assert [i["id"] for i in data2["items"]] == ids[2:4]
        assert data2["next_cursor"] is not None

        page3 = await client.get(
            url,
            params={"limit": 2, "cursor": data2["next_cursor"]},
            headers=auth_headers,
        )
        data3 = page3.json()
        assert [i["id"] for i in data3["items"]] == ids[4:5]
        assert data3["next_cursor"] is None


class TestGetItem:
    async def test_returns_existing_item(
        self,
        client: AsyncClient,
        order: OrderModel,
        item: ItemModel,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await client.get(
            f"{items_url(order.id)}/{item.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == item.id
        assert data["name"] == item.name
        assert data["price"] == item.price
        assert data["order_id"] == item.order_id

    async def test_not_found(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get(f"{items_url(order.id)}/9999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_another_users_item_returns_404(
        self,
        client: AsyncClient,
        make_item: ItemFactory,
        auth_headers: dict[str, str],
    ) -> None:
        elsewhere = await make_item()
        resp = await client.get(
            f"{items_url(elsewhere.order_id)}/{elsewhere.id}", headers=auth_headers
        )
        assert resp.status_code == 404
        assert resp.json()["error"] == "order_not_found"

    async def test_item_is_not_reachable_through_another_of_my_orders(
        self,
        client: AsyncClient,
        order: OrderModel,
        item: ItemModel,
        make_order: OrderFactory,
        user: UserModel,
        auth_headers: dict[str, str],
    ) -> None:
        """Both orders belong to the caller, so the order gate passes -- the
        item still must not be reachable through the wrong order's path."""
        my_other_order = await make_order(user=user)
        resp = await client.get(
            f"{items_url(my_other_order.id)}/{item.id}", headers=auth_headers
        )
        assert resp.status_code == 404
        assert resp.json()["error"] == "item_not_found"


class TestCreateItem:
    async def test_creates_and_returns_item(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        payload = {"name": "Pizza", "price": 12.50}
        resp = await client.post(
            f"{items_url(order.id)}/", json=payload, headers=auth_headers
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Pizza"
        assert data["price"] == 12.50
        # order_id is never sent -- it comes from the path
        assert data["order_id"] == order.id
        assert "id" in data

    async def test_missing_required_field_returns_422(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            f"{items_url(order.id)}/", json={"name": "Pizza"}, headers=auth_headers
        )
        assert resp.status_code == 422

    async def test_nonexistent_order_returns_404(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            f"{items_url(9999)}/",
            json={"name": "Ghost Item", "price": 5.0},
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["error"] == "order_not_found"

    async def test_cannot_add_to_another_users_order(
        self,
        client: AsyncClient,
        make_order: OrderFactory,
        auth_headers: dict[str, str],
    ) -> None:
        theirs = await make_order()
        resp = await client.post(
            f"{items_url(theirs.id)}/",
            json={"name": "Uninvited", "price": 5.0},
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["error"] == "order_not_found"


class TestUpdateItem:
    async def test_updates_name(
        self,
        client: AsyncClient,
        order: OrderModel,
        item: ItemModel,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await client.patch(
            f"{items_url(order.id)}/{item.id}",
            json={"name": "Salad"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Salad"

    async def test_patch_preserves_unchanged_fields(
        self,
        client: AsyncClient,
        order: OrderModel,
        item: ItemModel,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await client.patch(
            f"{items_url(order.id)}/{item.id}",
            json={"name": "Wrap"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["price"] == item.price

    async def test_updates_price(
        self,
        client: AsyncClient,
        order: OrderModel,
        item: ItemModel,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await client.patch(
            f"{items_url(order.id)}/{item.id}",
            json={"price": 19.99},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["price"] == 19.99

    async def test_not_found(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.patch(
            f"{items_url(order.id)}/9999", json={"name": "X"}, headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_cannot_update_another_users_item(
        self,
        client: AsyncClient,
        make_item: ItemFactory,
        auth_headers: dict[str, str],
    ) -> None:
        elsewhere = await make_item()
        resp = await client.patch(
            f"{items_url(elsewhere.order_id)}/{elsewhere.id}",
            json={"name": "Hijacked"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert elsewhere.name != "Hijacked"


class TestDeleteItem:
    async def test_deletes_item(
        self,
        client: AsyncClient,
        order: OrderModel,
        item: ItemModel,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await client.delete(
            f"{items_url(order.id)}/{item.id}", headers=auth_headers
        )
        assert resp.status_code == 204

        resp = await client.get(
            f"{items_url(order.id)}/{item.id}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_not_found(
        self, client: AsyncClient, order: OrderModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.delete(f"{items_url(order.id)}/9999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_cannot_delete_another_users_item(
        self,
        client: AsyncClient,
        make_item: ItemFactory,
        auth_headers: dict[str, str],
    ) -> None:
        elsewhere = await make_item()
        resp = await client.delete(
            f"{items_url(elsewhere.order_id)}/{elsewhere.id}", headers=auth_headers
        )
        assert resp.status_code == 404


class TestConfirmedOrderFreezesItems:
    """End to end over HTTP: once the order leaves PENDING its contents are fixed.

    The guard lives on OrderModel.assert_editable, so all three write paths get it
    from one place -- and reads keep working, because a placed order's contents
    are a record rather than a secret.
    """

    async def test_writes_are_refused_but_reads_continue(
        self,
        client: AsyncClient,
        order: OrderModel,
        item: ItemModel,
        auth_headers: dict[str, str],
    ) -> None:
        confirm = await client.patch(
            f"/api/v1/orders/{order.id}/status",
            json={"status": "confirmed"},
            headers=auth_headers,
        )
        assert confirm.status_code == 200

        added = await client.post(
            f"{items_url(order.id)}/",
            json={"name": "Late Addition", "price": 3.0},
            headers=auth_headers,
        )
        assert added.status_code == 409
        assert added.json()["error"] == "order_not_mutable"

        edited = await client.patch(
            f"{items_url(order.id)}/{item.id}",
            json={"name": "Renamed"},
            headers=auth_headers,
        )
        assert edited.status_code == 409

        removed = await client.delete(
            f"{items_url(order.id)}/{item.id}", headers=auth_headers
        )
        assert removed.status_code == 409

        listed = await client.get(f"{items_url(order.id)}/", headers=auth_headers)
        assert listed.status_code == 200
        assert [i["id"] for i in listed.json()["items"]] == [item.id]

        fetched = await client.get(
            f"{items_url(order.id)}/{item.id}", headers=auth_headers
        )
        assert fetched.status_code == 200
