from flash.repositories.user_repository import UserRepository
from flash.core.exceptions import UserNotFound
from flash.core.security import hash_password
from flash.models.user_model import UserModel
from flash.schemas.user_schema import UserCreate, UserUpdate


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def get(self, user_id: int) -> UserModel:
        user = await self._repo.get(user_id)
        if user is None:
            raise UserNotFound()
        return user

    async def create(self, data: UserCreate) -> UserModel:
        user = UserModel(
            username=data.username,
            email=data.email,
            password=hash_password(data.password),
        )
        user = await self._repo.create(user)
        await self._repo.commit()
        return user

    async def update(self, user_id: int, data: UserUpdate) -> UserModel:
        user = await self.get(user_id)
        user.username = data.username or user.username
        user.email = data.email or user.email
        if data.password:
            user.password = hash_password(data.password)
        await self._repo.commit()
        await self._repo.refresh(user)
        return user

    async def delete(self, user_id: int) -> None:
        user = await self.get(user_id)
        await self._repo.delete(user)
        await self._repo.commit()
