from collections.abc import Sequence
from typing import Protocol

from flash.core.exceptions import ItemNotFound, InvalidCursor
from flash.core.pagination import decode_cursor, encode_cursor
from flash.models.item_model import ItemModel
from flash.models.order_model import OrderModel
from flash.schemas.item_schema import ItemCreate, ItemUpdate


class ItemRepoProtocol(Protocol):
    async def get(self, entity_id: int) -> ItemModel | None: ...
    async def list_for_order_with_cursor(
        self, order_id: int, limit: int, cursor_id: int | None
    ) -> Sequence[ItemModel]: ...
    async def create(self, instance: ItemModel) -> ItemModel: ...
    async def delete(self, instance: ItemModel) -> None: ...
    async def commit(self) -> None: ...


class OrderAccessProtocol(Protocol):
    """The parent order's ownership gate, satisfied by OrderService.get.

    Items inherit the order's authorization rule instead of restating it.
    """

    async def get(self, order_id: int, actor_id: int) -> OrderModel: ...


class ItemService:
    def __init__(self, repo: ItemRepoProtocol, orders: OrderAccessProtocol) -> None:
        self._repo = repo
        self._orders = orders

    async def _item_in_order(self, order_id: int, item_id: int) -> ItemModel:
        """The item must belong to *this* order, or owning any order would reach it."""
        item = await self._repo.get(item_id)
        if item is None or item.order_id != order_id:
            raise ItemNotFound()
        return item

    async def _editable_order(self, order_id: int, actor_id: int) -> OrderModel:
        """Write gate: a reachable order that still accepts changes. Reads skip the
        editability check -- a placed order's items stay readable, just frozen."""
        order = await self._orders.get(order_id, actor_id)
        order.assert_editable()
        return order

    async def list_for_order(
        self, order_id: int, actor_id: int, limit: int, cursor: str | None
    ) -> tuple[list[ItemModel], str | None]:
        await self._orders.get(order_id, actor_id)
        cursor_id: int | None = None
        if cursor is not None:
            try:
                cursor_id = decode_cursor(cursor)
            except ValueError:
                raise InvalidCursor() from None
        items = list(
            await self._repo.list_for_order_with_cursor(order_id, limit, cursor_id)
        )
        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            next_cursor = encode_cursor(items[-1].id)
        return items, next_cursor

    async def get(self, order_id: int, item_id: int, actor_id: int) -> ItemModel:
        await self._orders.get(order_id, actor_id)
        return await self._item_in_order(order_id, item_id)

    async def create(self, order_id: int, data: ItemCreate, actor_id: int) -> ItemModel:
        await self._editable_order(order_id, actor_id)
        item = ItemModel(name=data.name, price=data.price, order_id=order_id)
        item = await self._repo.create(item)
        await self._repo.commit()
        return item

    async def update(
        self, order_id: int, item_id: int, data: ItemUpdate, actor_id: int
    ) -> ItemModel:
        await self._editable_order(order_id, actor_id)
        item = await self._item_in_order(order_id, item_id)
        # `is not None`, not `or`: price=0.0 is a real value.
        if data.name is not None:
            item.name = data.name
        if data.price is not None:
            item.price = data.price
        await self._repo.commit()
        return item

    async def delete(self, order_id: int, item_id: int, actor_id: int) -> None:
        await self._editable_order(order_id, actor_id)
        item = await self._item_in_order(order_id, item_id)
        await self._repo.delete(item)
        await self._repo.commit()
