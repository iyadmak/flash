import structlog
from typing import Protocol
from flash.core.exceptions import UserNotFound
from flash.core.security import hash_password
from flash.models.user_model import UserModel
from flash.schemas.user_schema import UserCreate, UserUpdate

logger = structlog.get_logger()


class UserRepositoryProtocol(Protocol):
    async def get(self, user_id: int) -> UserModel | None: ...
    async def create(self, instance: UserModel) -> UserModel: ...
    async def delete(self, instance: UserModel) -> None: ...
    async def commit(self) -> None: ...
    async def refresh(self, instance: UserModel) -> None: ...


class UserService:
    def __init__(self, repo: UserRepositoryProtocol) -> None:
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
        logger.info("user_created", user_id=user.id, username=user.username)
        return user

    async def update(self, user_id: int, data: UserUpdate) -> UserModel:
        user = await self.get(user_id)
        changed_fields = []
        if data.username is not None:
            user.username = data.username
            changed_fields.append("username")
        if data.email is not None:
            user.email = data.email
            changed_fields.append("email")
        if data.password is not None:
            user.password = hash_password(data.password)
            changed_fields.append("password")
        if data.is_verified is not None:
            user.is_verified = data.is_verified
            changed_fields.append("is_verified")
        if data.is_active is not None:
            user.is_active = data.is_active
            changed_fields.append("is_active")
        await self._repo.commit()
        await self._repo.refresh(user)
        logger.info("user_updated", user_id=user.id, changed_fields=changed_fields)
        return user

    async def delete(self, user_id: int) -> None:
        user = await self.get(user_id)
        await self._repo.delete(user)
        await self._repo.commit()
        logger.info("user_deleted", user_id=user_id)
