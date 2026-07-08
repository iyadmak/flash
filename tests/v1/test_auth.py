from httpx import AsyncClient
from flash.models.user_model import UserModel
from tests.v1.conftest import UserFactory

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


class TestLogin:
    async def test_returns_access_token_for_correct_credentials(
        self, client: AsyncClient, make_user: UserFactory
    ) -> None:
        user = await make_user(password="correct-password")
        response = await client.post(
            f"{BASE}/login",
            data={"username": user.email, "password": "correct-password"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_wrong_password_returns_401(
        self, client: AsyncClient, make_user: UserFactory
    ) -> None:
        user = await make_user(password="correct-password")
        response = await client.post(
            f"{BASE}/login",
            data={"username": user.email, "password": "wrong-password"},
        )
        assert response.status_code == 401

    async def test_nonexistent_email_returns_401(self, client: AsyncClient) -> None:
        response = await client.post(
            f"{BASE}/login",
            data={"username": "nobody@example.com", "password": "whatever123"},
        )
        assert response.status_code == 401


class TestLoginRateLimit:
    async def test_blocks_after_too_many_attempts(self, client: AsyncClient) -> None:
        for _ in range(5):
            await client.post(
                f"{BASE}/login", data={"username": "x@example.com", "password": "wrong"}
            )
        response = await client.post(
            f"{BASE}/login", data={"username": "x@example.com", "password": "wrong"}
        )
        assert response.status_code == 429


class TestPasswordReset:
    async def test_request_for_existing_email_returns_202(
        self, client: AsyncClient, user: UserModel
    ) -> None:
        response = await client.post(
            f"{BASE}/password-reset/request", json={"email": user.email}
        )
        assert response.status_code == 202

    async def test_request_for_unknown_email_also_returns_202(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            f"{BASE}/password-reset/request", json={"email": "nobody@example.com"}
        )
        assert response.status_code == 202

    async def test_confirm_with_bad_token_returns_401(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            f"{BASE}/password-reset/confirm",
            json={"token": "not-a-real-token", "new_password": "newpassword123"},
        )
        assert response.status_code == 401
