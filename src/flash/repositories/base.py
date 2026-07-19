from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from flash.core.db import Base
from flash.core.exceptions import DeleteConflict
from flash.core.integrity import is_foreign_key_violation, translate_integrity_error


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

    async def list_witt_cursor(
        self, limit: int, cursor_id: int | None
    ) -> Sequence[ModelT]:
        query = select(self._model).order_by(self._model.id).limit(limit + 1)
        if cursor_id is not None:
            query = query.where(self._model.id > cursor_id)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def create(self, instance: ModelT) -> ModelT:
        self._session.add(instance)
        try:
            await self._session.flush()
        except IntegrityError as e:
            translate_integrity_error(e)
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self._session.delete(instance)
        try:
            await self._session.commit()
        except IntegrityError as e:
            if is_foreign_key_violation(e):
                raise DeleteConflict() from e
            raise

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as e:
            translate_integrity_error(e)

    async def refresh(self, instance: ModelT) -> None:
        await self._session.refresh(instance)
