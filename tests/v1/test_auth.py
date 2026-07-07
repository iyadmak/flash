from httpx import AsyncClient
from flash.models.user_model import UserModel

BASE = "/api/v1/auth"


class TestRegister:
    async def test_create_and_return_user(self, client: AsyncClient) -> None:
        response = await client.post(
            f"{BASE}/register",
            json={
                "email": "test@user.me",
                "username": "test_user",
                "password": "normalpassword",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@user.me"
        assert data["username"] == "test_user"

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, user: UserModel
    ) -> None:
        response = await client.post(
            f"{BASE}/register",
            json={
                "email": user.email,
                "username": "someoneelse",
                "password": "password123",
            },
        )
        assert response.status_code == 409

    async def test_short_password_returns_422(self, client: AsyncClient) -> None:
        response = await client.post(
            f"{BASE}/register",
            json={
                "email": "short@example.com",
                "username": "shortpw",
                "password": "abc",
            },
        )
        assert response.status_code == 422
