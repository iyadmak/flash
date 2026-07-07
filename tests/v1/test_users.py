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
