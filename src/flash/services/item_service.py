"""Item Service"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flash.core.exceptions import ItemNotFound
from flash.models.item import ItemModel
from flash.schemas.item import ItemCreate, ItemUpdate


class ItemService:
    """Item Service"""

    async def list(self, session: AsyncSession) -> list[ItemModel]:
        """List all items"""
        items = await session.execute(select(ItemModel))
        return list(items.scalars().all())

    async def get(self, session: AsyncSession, item_id: int) -> ItemModel:
        """Get an item by ID"""
        item = await session.get(ItemModel, item_id)
        if not item:
            raise ItemNotFound()
        return item

    async def create(self, session: AsyncSession, data: ItemCreate) -> ItemModel:
        """Create an item"""
        item = ItemModel(name=data.name, price=data.price)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item

    async def update(
        self, session: AsyncSession, item_id: int, data: ItemUpdate
    ) -> ItemModel:
        """Update an item"""
        item = await self.get(session, item_id)
        if data.name is not None:
            item.name = data.name
        if data.price is not None:
            item.price = data.price
        await session.commit()
        await session.refresh(item)
        return item

    async def delete(self, session: AsyncSession, item_id: int) -> None:
        """Delete an item"""
        item = await self.get(session, item_id)
        await session.delete(item)
        await session.commit()
