from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from flash.repositories.base import BaseRepository
from flash.models.user_model import UserModel
from flash.core.exceptions import EmailAlreadyRegistered, UniqueConstraintViolation


class UserRepository(BaseRepository[UserModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserModel)

    async def get_by_email(self, email: str) -> UserModel | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, instance: UserModel) -> UserModel:
        try:
            return await super().create(instance)
        except UniqueConstraintViolation:
            raise EmailAlreadyRegistered() from None

    async def commit(self) -> None:
        try:
            await super().commit()
        except UniqueConstraintViolation:
            raise EmailAlreadyRegistered() from None
