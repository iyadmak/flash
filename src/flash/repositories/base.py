from collections.abc import Sequence
from typing import NoReturn
from asyncpg.exceptions import ForeignKeyViolationError as PGForeignKeyViolationError
from asyncpg.exceptions import UniqueViolationError as PGUniqueViolationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from flash.core.db import Base
from flash.core.exceptions import (
    DeleteConflict,
    ForeignKeyViolation,
    UniqueConstraintViolation,
)


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

    def _translate_integrity_error(self, e: IntegrityError) -> NoReturn:
        # Column-specific: which parent table an FK/unique violation maps to
        # is something only the caller's context can resolve, so this raises
        # the generic, constraint-name-carrying exception for a specific
        # repository to catch and translate into a domain AppError.
        assert e.orig is not None
        cause = e.orig.__cause__
        if isinstance(cause, PGForeignKeyViolationError):
            raise ForeignKeyViolation(cause.constraint_name) from e
        if isinstance(cause, PGUniqueViolationError):
            raise UniqueConstraintViolation(cause.constraint_name) from e
        raise e

    async def create(self, instance: ModelT) -> ModelT:
        self._session.add(instance)
        try:
            await self._session.flush()
        except IntegrityError as e:
            self._translate_integrity_error(e)
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        # Unlike create()/commit(), an FK violation here always means the
        # same thing regardless of which table blocks it -- some other row
        # still references this one -- so it's resolved directly to a
        # domain AppError, with no per-repository translation needed.
        await self._session.delete(instance)
        try:
            await self._session.commit()
        except IntegrityError as e:
            assert e.orig is not None
            if isinstance(e.orig.__cause__, PGForeignKeyViolationError):
                raise DeleteConflict() from e
            raise

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as e:
            self._translate_integrity_error(e)

    async def refresh(self, instance: ModelT) -> None:
        await self._session.refresh(instance)
