from flash.repositories.user_repository import UserRepository
from flash.models.user_model import UserModel
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_create_and_get_user(async_session: AsyncSession) -> None:
    repo = UserRepository(async_session)

    user = await repo.create(
        UserModel(email="test@example.com", username="iyad", password="password")
    )
    await async_session.commit()

    fetched = await repo.get(user.id)
    assert fetched is not None
    assert fetched.email == "test@example.com"


async def test_create_user_endpoint(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users/",
        json={"email": "a@b.com", "username": "iyad", "password": "password"},
    )
    assert response.status_code == 201
