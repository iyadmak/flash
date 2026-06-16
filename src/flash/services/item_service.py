from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flash.core.exceptions import ItemNotFound
from flash.models.item_model import ItemModel
from flash.schemas.item_schema import ItemCreate, ItemUpdate


class ItemService:
    async def list(self, session: AsyncSession) -> list[ItemModel]:
        items = await session.execute(select(ItemModel))
        return list(items.scalars().all())

    async def get(self, session: AsyncSession, item_id: int) -> ItemModel:
        item = await session.get(ItemModel, item_id)
        if not item:
            raise ItemNotFound()
        return item

    async def create(self, session: AsyncSession, data: ItemCreate) -> ItemModel:
        item = ItemModel(name=data.name, price=data.price)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item

    async def update(
        self, session: AsyncSession, item_id: int, data: ItemUpdate
    ) -> ItemModel:
        item = await self.get(session, item_id)
        item.name = data.name or item.name
        item.price = data.price or item.price
        await session.commit()
        await session.refresh(item)
        return item

    async def delete(self, session: AsyncSession, item_id: int) -> None:
        item = await self.get(session, item_id)
        await session.delete(item)
        await session.commit()
