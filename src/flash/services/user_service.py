from sqlalchemy.ext.asyncio import AsyncSession

from flash.core.exceptions import UserNotFound
from flash.core.security import hash_password
from flash.models.user_model import UserModel
from flash.schemas.user_schema import UserCreate, UserUpdate


class UserService:
    async def get(self, session: AsyncSession, user_id: int) -> UserModel:
        user = await session.get(UserModel, user_id)
        if user is None:
            raise UserNotFound()
        return user

    async def create(self, session: AsyncSession, data: UserCreate) -> UserModel:
        user = UserModel(
            username=data.username,
            email=data.email,
            password=hash_password(data.password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def update(
        self, session: AsyncSession, user_id: int, data: UserUpdate
    ) -> UserModel:
        user = await self.get(session, user_id)
        user.username = data.username or user.username
        user.email = data.email or user.email
        if data.password:
            user.password = hash_password(data.password)

        await session.commit()
        await session.refresh(user)
        return user

    async def delete(self, session: AsyncSession, user_id: int) -> None:
        user = await self.get(session, user_id)
        await session.delete(user)
        await session.commit()
