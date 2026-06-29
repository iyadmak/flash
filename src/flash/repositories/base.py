from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from flash.core.db import Base


class BaseRepository[ModelT: Base]:
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    async def get(self, id: int) -> ModelT | None:
        return await self._session.get(self._model, id)

    async def list(self, limit: int, offset: int) -> Sequence[ModelT]:
        result = await self._session.execute(
            select(self._model).limit(limit).offset(offset).order_by(self._model.id)
        )
        return result.scalars().all()

    async def create(self, instance: ModelT) -> ModelT:
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self._session.delete(instance)
        await self._session.commit()

    async def commit(self) -> None:
        await self._session.commit()
