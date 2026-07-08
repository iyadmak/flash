from flash.core.exceptions import ItemNotFound, InvalidCursor
from flash.models.item_model import ItemModel
from flash.schemas.item_schema import ItemCreate, ItemUpdate
from flash.repositories.item_repository import ItemRepository
from flash.core.pagination import decode_cursor, encode_cursor


class ItemService:
    def __init__(self, repo: ItemRepository) -> None:
        self._repo = repo

    async def get(self, item_id: int) -> ItemModel:
        item = await self._repo.get(item_id)
        if item is None:
            raise ItemNotFound()
        return item

    async def list_with_cursor(
        self, limit: int, cursor: str | None
    ) -> tuple[list[ItemModel], str | None]:
        cursor_id: int | None = None
        if cursor is not None:
            try:
                cursor_id = decode_cursor(cursor)
            except ValueError:
                raise InvalidCursor() from None
        items = list(await self._repo.list_witt_cursor(limit, cursor_id))
        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            next_cursor = encode_cursor(items[-1].id)
        return items, next_cursor

    async def create(self, data: ItemCreate) -> ItemModel:
        item = ItemModel(name=data.name, price=data.price, order_id=data.order_id)
        item = await self._repo.create(item)
        await self._repo.commit()
        return item

    async def update(self, item_id: int, data: ItemUpdate) -> ItemModel:
        item = await self.get(item_id)
        item.name = data.name or item.name
        item.price = data.price or item.price
        await self._repo.commit()
        return item

    async def delete(self, item_id: int) -> None:
        item = await self.get(item_id)
        await self._repo.delete(item)
        await self._repo.commit()
