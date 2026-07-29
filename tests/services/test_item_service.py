"""Unit tests for ItemService — no DB, no HTTP, just the service against fakes.

Items carry no authorization rule of their own; every operation delegates to the
parent order's gate, which FakeOrderAccess stands in for.
"""

import pytest

from flash.core.exceptions import (
    InvalidCursor,
    ItemNotFound,
    OrderNotFound,
    OrderNotMutable,
)
from flash.core.pagination import encode_cursor
from flash.domain.order_status import OrderStatus
from flash.models.item_model import ItemModel
from flash.models.order_model import OrderModel
from flash.schemas.item_schema import ItemCreate, ItemUpdate
from flash.services.item_service import ItemService

ACTOR_ID = 1
OTHER_ACTOR_ID = 2
MY_ORDER_ID = 10
MY_OTHER_ORDER_ID = 11
THEIR_ORDER_ID = 20
MY_DELIVERED_ORDER_ID = 12


class FakeOrderAccess:
    """Stands in for OrderService.get, the gate items delegate to.

    Returns a real OrderModel: assert_editable() is the rule under test, so
    stubbing it away would test nothing.
    """

    def __init__(
        self, owners: dict[int, int], statuses: dict[int, OrderStatus] | None = None
    ) -> None:
        self._owners = owners
        self._statuses = statuses or {}
        self.calls: list[tuple[int, int]] = []

    async def get(self, order_id: int, actor_id: int) -> OrderModel:
        self.calls.append((order_id, actor_id))
        owner = self._owners.get(order_id)
        if owner is None or owner != actor_id:
            raise OrderNotFound()
        return OrderModel(
            id=order_id,
            user_id=owner,
            restaurant_id=99,
            total_price=42.50,
            status=self._statuses.get(order_id, OrderStatus.PENDING),
        )


class FakeItemRepository:
    def __init__(self) -> None:
        self._items: dict[int, ItemModel] = {}
        self._next_id = 1
        self.commit_calls = 0

    def seed(self, item: ItemModel) -> ItemModel:
        item.id = self._next_id
        self._next_id += 1
        self._items[item.id] = item
        return item

    async def get(self, entity_id: int) -> ItemModel | None:
        return self._items.get(entity_id)

    async def list_for_order_with_cursor(
        self, order_id: int, limit: int, cursor_id: int | None
    ) -> list[ItemModel]:
        rows = sorted(
            (i for i in self._items.values() if i.order_id == order_id),
            key=lambda i: i.id,
        )
        if cursor_id is not None:
            rows = [i for i in rows if i.id > cursor_id]
        return rows[: limit + 1]

    async def create(self, instance: ItemModel) -> ItemModel:
        return self.seed(instance)

    async def delete(self, instance: ItemModel) -> None:
        self._items.pop(instance.id, None)

    async def commit(self) -> None:
        self.commit_calls += 1


@pytest.fixture
def orders() -> FakeOrderAccess:
    return FakeOrderAccess(
        owners={
            MY_ORDER_ID: ACTOR_ID,
            MY_OTHER_ORDER_ID: ACTOR_ID,
            MY_DELIVERED_ORDER_ID: ACTOR_ID,
            THEIR_ORDER_ID: 99,
        },
        statuses={MY_DELIVERED_ORDER_ID: OrderStatus.DELIVERED},
    )


@pytest.fixture
def repo() -> FakeItemRepository:
    return FakeItemRepository()


@pytest.fixture
def service(repo: FakeItemRepository, orders: FakeOrderAccess) -> ItemService:
    return ItemService(repo, orders)


def an_item(order_id: int, name: str = "Burger", price: float = 9.99) -> ItemModel:
    return ItemModel(order_id=order_id, name=name, price=price)


class TestGet:
    async def test_returns_item_on_own_order(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        seeded = repo.seed(an_item(MY_ORDER_ID))
        assert await service.get(MY_ORDER_ID, seeded.id, ACTOR_ID) is seeded

    async def test_order_gate_runs_before_the_item_lookup(
        self, service: ItemService, repo: FakeItemRepository, orders: FakeOrderAccess
    ) -> None:
        """An item on somebody else's order surfaces as OrderNotFound, not
        ItemNotFound -- the gate refuses before the item is ever fetched."""
        seeded = repo.seed(an_item(THEIR_ORDER_ID))
        with pytest.raises(OrderNotFound):
            await service.get(THEIR_ORDER_ID, seeded.id, ACTOR_ID)
        assert orders.calls == [(THEIR_ORDER_ID, ACTOR_ID)]

    async def test_item_from_a_different_order_is_not_found(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        """The second check, and the reason it exists: the actor owns both
        orders, so the gate passes -- but an item on order 11 must not be
        reachable through order 10's path."""
        seeded = repo.seed(an_item(MY_OTHER_ORDER_ID))
        with pytest.raises(ItemNotFound):
            await service.get(MY_ORDER_ID, seeded.id, ACTOR_ID)

    async def test_missing_item_is_not_found(self, service: ItemService) -> None:
        with pytest.raises(ItemNotFound):
            await service.get(MY_ORDER_ID, 999, ACTOR_ID)


class TestListForOrder:
    async def test_returns_only_items_on_that_order(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        mine = repo.seed(an_item(MY_ORDER_ID))
        elsewhere = repo.seed(an_item(MY_OTHER_ORDER_ID))
        items, next_cursor = await service.list_for_order(
            MY_ORDER_ID, ACTOR_ID, 50, None
        )
        assert [i.id for i in items] == [mine.id]
        assert elsewhere.id not in [i.id for i in items]
        assert next_cursor is None

    async def test_refuses_another_users_order(self, service: ItemService) -> None:
        with pytest.raises(OrderNotFound):
            await service.list_for_order(THEIR_ORDER_ID, ACTOR_ID, 50, None)

    async def test_paginates_with_cursor(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        seeded = [repo.seed(an_item(MY_ORDER_ID)) for _ in range(3)]

        first, cursor = await service.list_for_order(MY_ORDER_ID, ACTOR_ID, 2, None)
        assert [i.id for i in first] == [seeded[0].id, seeded[1].id]
        assert cursor == encode_cursor(seeded[1].id)

        second, cursor = await service.list_for_order(MY_ORDER_ID, ACTOR_ID, 2, cursor)
        assert [i.id for i in second] == [seeded[2].id]
        assert cursor is None

    async def test_rejects_a_malformed_cursor(self, service: ItemService) -> None:
        with pytest.raises(InvalidCursor):
            await service.list_for_order(MY_ORDER_ID, ACTOR_ID, 50, "not-base64!")


class TestCreate:
    async def test_order_id_comes_from_the_path(self, service: ItemService) -> None:
        created = await service.create(
            MY_ORDER_ID, ItemCreate(name="Pizza", price=12.50), ACTOR_ID
        )
        assert created.order_id == MY_ORDER_ID
        assert created.name == "Pizza"

    async def test_refuses_another_users_order(self, service: ItemService) -> None:
        with pytest.raises(OrderNotFound):
            await service.create(
                THEIR_ORDER_ID, ItemCreate(name="Pizza", price=12.50), ACTOR_ID
            )


class TestUpdate:
    async def test_updates_own_item(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        seeded = repo.seed(an_item(MY_ORDER_ID))
        updated = await service.update(
            MY_ORDER_ID, seeded.id, ItemUpdate(name="Salad"), ACTOR_ID
        )
        assert updated.name == "Salad"
        assert updated.price == 9.99

    async def test_zero_price_is_applied_not_skipped(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        """Regression test for the `or` idiom: `data.price or item.price` reads
        0.0 as "unset" and refuses to apply a legitimate free item."""
        seeded = repo.seed(an_item(MY_ORDER_ID))
        updated = await service.update(
            MY_ORDER_ID, seeded.id, ItemUpdate(price=0.0), ACTOR_ID
        )
        assert updated.price == 0.0

    async def test_refuses_another_users_order(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        seeded = repo.seed(an_item(THEIR_ORDER_ID))
        with pytest.raises(OrderNotFound):
            await service.update(
                THEIR_ORDER_ID, seeded.id, ItemUpdate(name="Hijacked"), ACTOR_ID
            )
        assert seeded.name == "Burger"


class TestDelete:
    async def test_deletes_own_item(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        seeded = repo.seed(an_item(MY_ORDER_ID))
        await service.delete(MY_ORDER_ID, seeded.id, ACTOR_ID)
        assert await repo.get(seeded.id) is None

    async def test_refuses_another_users_order(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        seeded = repo.seed(an_item(THEIR_ORDER_ID))
        with pytest.raises(OrderNotFound):
            await service.delete(THEIR_ORDER_ID, seeded.id, ACTOR_ID)
        assert await repo.get(seeded.id) is seeded

    async def test_cannot_delete_through_a_different_order(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        seeded = repo.seed(an_item(MY_OTHER_ORDER_ID))
        with pytest.raises(ItemNotFound):
            await service.delete(MY_ORDER_ID, seeded.id, ACTOR_ID)
        assert await repo.get(seeded.id) is seeded


class TestOrderMustBeEditable:
    """Writes go through OrderModel.assert_editable, reads do not.

    The actor owns the delivered order, so only its lifecycle position stops the
    write -- and the guard sits on the model, so new write paths inherit it.
    """

    async def test_cannot_add_an_item(self, service: ItemService) -> None:
        with pytest.raises(OrderNotMutable):
            await service.create(
                MY_DELIVERED_ORDER_ID, ItemCreate(name="Late", price=5.0), ACTOR_ID
            )

    async def test_cannot_update_an_item(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        seeded = repo.seed(an_item(MY_DELIVERED_ORDER_ID))
        with pytest.raises(OrderNotMutable):
            await service.update(
                MY_DELIVERED_ORDER_ID, seeded.id, ItemUpdate(name="Edited"), ACTOR_ID
            )
        assert seeded.name == "Burger"

    async def test_cannot_delete_an_item(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        seeded = repo.seed(an_item(MY_DELIVERED_ORDER_ID))
        with pytest.raises(OrderNotMutable):
            await service.delete(MY_DELIVERED_ORDER_ID, seeded.id, ACTOR_ID)
        assert await repo.get(seeded.id) is seeded

    async def test_items_stay_readable(
        self, service: ItemService, repo: FakeItemRepository
    ) -> None:
        """A delivered order is a record: its contents are frozen, not hidden."""
        seeded = repo.seed(an_item(MY_DELIVERED_ORDER_ID))
        assert await service.get(MY_DELIVERED_ORDER_ID, seeded.id, ACTOR_ID) is seeded
        items, _ = await service.list_for_order(
            MY_DELIVERED_ORDER_ID, ACTOR_ID, 50, None
        )
        assert [i.id for i in items] == [seeded.id]
