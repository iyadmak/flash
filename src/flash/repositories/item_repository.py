from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from flash.repositories.base import BaseRepository
from flash.models.item_model import ItemModel


class ItemRepository(BaseRepository[ItemModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ItemModel)

    async def get_by_name(self, name: str) -> ItemModel | None:
        result = await self._session.execute(
            select(ItemModel).where(ItemModel.name == name)
        )
        return result.scalar_one_or_none()
