"""Unit tests for UserService — no DB, no HTTP, just the service against a fake repo."""

import pytest

from flash.core.exceptions import UserNotFound
from flash.core.security import verify_password
from flash.models.user_model import UserModel
from flash.schemas.user_schema import UserCreate, UserUpdate
from flash.services.user_service import UserService


class FakeUserRepository:
    """In-memory stand-in — satisfies UserRepositoryProtocol structurally,
    no inheritance from UserRepository needed."""

    def __init__(self) -> None:
        self._users: dict[int, UserModel] = {}
        self._next_id = 1

    def seed(self, user: UserModel) -> UserModel:
        """Insert a fully-formed user directly — for setting up state that
        UserCreate can't express (e.g. is_active)."""
        user.id = self._next_id
        self._next_id += 1
        self._users[user.id] = user
        return user

    async def get(self, id: int) -> UserModel | None:
        return self._users.get(id)

    async def create(self, instance: UserModel) -> UserModel:
        return self.seed(instance)

    async def delete(self, instance: UserModel) -> None:
        self._users.pop(instance.id, None)

    async def commit(self) -> None:
        pass

    async def refresh(self, instance: UserModel) -> None:
        pass


@pytest.fixture
def repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def service(repo: FakeUserRepository) -> UserService:
    return UserService(repo)


class TestGet:
    async def test_raises_not_found_when_missing(self, service: UserService) -> None:
        with pytest.raises(UserNotFound):
            await service.get(999)

    async def test_returns_existing_user(self, service: UserService) -> None:
        created = await service.create(
            UserCreate(username="iyad", email="iyad@example.com", password="secret123")
        )
        fetched = await service.get(created.id)
        assert fetched is created


class TestCreate:
    async def test_hashes_the_password(self, service: UserService) -> None:
        user = await service.create(
            UserCreate(username="iyad", email="iyad@example.com", password="secret123")
        )
        assert user.password != "secret123"
        assert verify_password("secret123", user.password)


class TestUpdate:
    async def test_updates_username(self, service: UserService) -> None:
        user = await service.create(
            UserCreate(username="old", email="old@example.com", password="secret123")
        )
        updated = await service.update(user.id, UserUpdate(username="new"))
        assert updated.username == "new"

    async def test_is_active_flag_is_silently_ignored(
        self, service: UserService, repo: FakeUserRepository
    ) -> None:
        """Documents a real bug: UserUpdate.is_active exists on the schema
        but UserService.update never applies it."""
        seeded = repo.seed(
            UserModel(
                username="iyad",
                email="iyad@example.com",
                password="hashed",
                is_active=True,
            )
        )
        updated = await service.update(seeded.id, UserUpdate(is_active=False))
        assert updated.is_active is False


class TestDelete:
    async def test_removes_user(self, service: UserService) -> None:
        user = await service.create(
            UserCreate(username="iyad", email="iyad@example.com", password="secret123")
        )
        await service.delete(user.id)
        with pytest.raises(UserNotFound):
            await service.get(user.id)
