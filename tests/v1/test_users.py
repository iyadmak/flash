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

    async def test_email_already_taken_returns_409(
        self,
        client: AsyncClient,
        user: UserModel,
        make_user: UserFactory,
        auth_headers: dict[str, str],
    ) -> None:
        other = await make_user(email="taken@example.com")
        resp = await client.put(
            f"/api/v1/users/{user.id}",
            json={"email": other.email},
            headers=auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["error"] == "email_already_registered"


class TestGetMe:
    async def test_returns_the_logged_in_user(
        self, client: AsyncClient, user: UserModel, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/users/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == user.id
        assert data["email"] == user.email

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401
