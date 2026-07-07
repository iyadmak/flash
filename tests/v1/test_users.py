from flash.repositories.user_repository import UserRepository
from flash.models.user_model import UserModel
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from .conftest import UserFactory


async def test_create_and_get_user(async_session: AsyncSession) -> None:
    repo = UserRepository(async_session)

    user = await repo.create(
        UserModel(email="test@example.com", username="iyad", password="password")
    )
    await async_session.commit()

    fetched = await repo.get(user.id)
    assert fetched is not None
    assert fetched.email == "test@example.com"


async def test_get_returns_inactive_user(
    client: AsyncClient, make_user: UserFactory
) -> None:
    inactive = await make_user(is_active=False)
    resp = await client.get(f"/api/v1/users/{inactive.id}")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


class TestUpdate:
    async def test_updates_own_username(
        self, client: AsyncClient, user: UserModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.put(
            f"/api/v1/users/{user.id}", json={"username": "new"}, headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_requires_authentication(
        self, client: AsyncClient, user: UserModel
    ) -> None:
        resp = await client.put(f"/api/v1/users/{user.id}", json={"username": "new"})
        assert resp.status_code == 401

    async def test_cannot_update_another_user(
        self,
        client: AsyncClient,
        user: UserModel,
        make_user: UserFactory,
        auth_headers: dict[str, str],
    ) -> None:
        other = await make_user()
        resp = await client.put(
            f"/api/v1/users/{other.id}",
            json={"username": "hijacked"},
            headers=auth_headers,
        )
        assert resp.status_code == 403
