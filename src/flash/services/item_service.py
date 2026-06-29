from flash.core.exceptions import ItemNotFound
from flash.models.item_model import ItemModel
from flash.schemas.item_schema import ItemCreate, ItemUpdate
from flash.repositories.item_repository import ItemRepository


class ItemService:
    def __init__(self, repo: ItemRepository) -> None:
        self._repo = repo

    async def get(self, item_id: int) -> ItemModel:
        item = await self._repo.get(item_id)
        if item is None:
            raise ItemNotFound()
        return item

    async def list(self, limit: int, offset: int) -> list[ItemModel]:
        return list(await self._repo.list(limit, offset))

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
