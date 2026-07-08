from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from flash.repositories.base import BaseRepository
from flash.models.password_reset_token_model import PasswordResetTokenModel


class PasswordResetTokenRepository(BaseRepository[PasswordResetTokenModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PasswordResetTokenModel)

    async def get_by_token_hash(
        self, token_hash: str
    ) -> PasswordResetTokenModel | None:
        result = await self._session.execute(
            select(PasswordResetTokenModel).where(
                PasswordResetTokenModel.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()
