from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from flash.repositories.base import BaseRepository
from flash.models.item_model import ItemModel
from flash.core.exceptions import ForeignKeyViolation, OrderNotFound


class ItemRepository(BaseRepository[ItemModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ItemModel)

    async def list_for_order_with_cursor(
        self, order_id: int, limit: int, cursor_id: int | None
    ) -> Sequence[ItemModel]:
        # limit + 1 so the service can tell whether another page exists without
        # a second count query. Covered by ix_items_order_id.
        query = (
            select(ItemModel)
            .where(ItemModel.order_id == order_id)
            .order_by(ItemModel.id)
            .limit(limit + 1)
        )
        if cursor_id is not None:
            query = query.where(ItemModel.id > cursor_id)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def create(self, instance: ItemModel) -> ItemModel:
        try:
            return await super().create(instance)
        except ForeignKeyViolation as e:
            if e.constraint_name == "fk_items_order_id_orders":
                raise OrderNotFound() from None
            raise
