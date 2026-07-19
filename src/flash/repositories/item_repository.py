from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from flash.repositories.base import BaseRepository
from flash.models.item_model import ItemModel
from flash.core.exceptions import ForeignKeyViolation, OrderNotFound


class ItemRepository(BaseRepository[ItemModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ItemModel)

    async def get_by_name(self, name: str) -> ItemModel | None:
        result = await self._session.execute(
            select(ItemModel).where(ItemModel.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, instance: ItemModel) -> ItemModel:
        try:
            return await super().create(instance)
        except ForeignKeyViolation as e:
            if e.constraint_name == "fk_items_order_id_orders":
                raise OrderNotFound() from None
            raise
