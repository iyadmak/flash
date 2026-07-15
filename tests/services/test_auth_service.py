"""Unit tests for AuthService — no DB, no HTTP, just the service against fakes."""

from datetime import datetime, timedelta, timezone

import pytest

from flash.core.exceptions import InvalidCredentials, InvalidToken
from flash.core.security import hash_password, verify_password
from flash.models.password_reset_token_model import PasswordResetTokenModel
from flash.models.user_model import UserModel
from flash.services.auth_service import AuthService, _hash_token


class FakeUserRepository:
    def __init__(self) -> None:
        self._users: dict[int, UserModel] = {}
        self._next_id = 1

    def seed(self, user: UserModel) -> UserModel:
        user.id = self._next_id
        self._next_id += 1
        self._users[user.id] = user
        return user

    async def get(self, id: int) -> UserModel | None:
        return self._users.get(id)

    async def get_by_email(self, email: str) -> UserModel | None:
        return next((u for u in self._users.values() if u.email == email), None)


class FakePasswordResetTokenRepository:
    def __init__(self) -> None:
        self._tokens: dict[int, PasswordResetTokenModel] = {}
        self._next_id = 1

    async def create(
        self, instance: PasswordResetTokenModel
    ) -> PasswordResetTokenModel:
        instance.id = self._next_id
        self._next_id += 1
        self._tokens[instance.id] = instance
        return instance

    async def get_by_token_hash(
        self, token_hash: str
    ) -> PasswordResetTokenModel | None:
        return next(
            (t for t in self._tokens.values() if t.token_hash == token_hash), None
        )

    async def commit(self) -> None:
        pass


class FakeCache:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    async def get(self, name: str, /) -> str | None:
        return self._data.get(name)

    async def set(self, name: str, value: str, ex: int | None = None) -> None:
        self._data[name] = value

    async def delete(self, *names: str) -> None:
        for name in names:
            self._data.pop(name, None)


@pytest.fixture
def user_repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def reset_token_repo() -> FakePasswordResetTokenRepository:
    return FakePasswordResetTokenRepository()


@pytest.fixture
def cache() -> FakeCache:
    return FakeCache()


@pytest.fixture
def service(
    user_repo: FakeUserRepository,
    reset_token_repo: FakePasswordResetTokenRepository,
    cache: FakeCache,
) -> AuthService:
    return AuthService(user_repo, reset_token_repo, cache)


def _make_user(
    email: str = "iyad@example.com", password: str = "old-password"
) -> UserModel:
    now = datetime.now(timezone.utc)
    return UserModel(
        username="iyad",
        email=email,
        password=hash_password(password),
        is_active=True,
        is_verified=False,
        created_at=now,
        updated_at=now,
    )


class TestLogin:
    async def test_returns_token_for_correct_credentials(
        self, service: AuthService, user_repo: FakeUserRepository
    ) -> None:
        user_repo.seed(_make_user(password="correct-password"))
        token = await service.login("iyad@example.com", "correct-password")
        assert isinstance(token, str) and token

    async def test_wrong_password_raises_invalid_credentials(
        self, service: AuthService, user_repo: FakeUserRepository
    ) -> None:
        user_repo.seed(_make_user(password="correct-password"))
        with pytest.raises(InvalidCredentials):
            await service.login("iyad@example.com", "wrong-password")

    async def test_unknown_email_raises_invalid_credentials(
        self, service: AuthService
    ) -> None:
        with pytest.raises(InvalidCredentials):
            await service.login("nobody@example.com", "whatever123")


class TestGetCurrentUser:
    async def test_valid_token_returns_the_user(
        self, service: AuthService, user_repo: FakeUserRepository
    ) -> None:
        user = user_repo.seed(_make_user())
        token = await service.login("iyad@example.com", "old-password")
        current = await service.get_current_user(token)
        assert current.id == user.id

    async def test_garbage_token_raises_invalid_token(
        self, service: AuthService
    ) -> None:
        with pytest.raises(InvalidToken):
            await service.get_current_user("not-a-real-jwt")

    async def test_inactive_user_raises_invalid_token(
        self, service: AuthService, user_repo: FakeUserRepository
    ) -> None:
        user_repo.seed(_make_user())
        token = await service.login("iyad@example.com", "old-password")
        user_repo._users[1].is_active = False
        with pytest.raises(InvalidToken):
            await service.get_current_user(token)


class TestRevokeAllSessions:
    async def test_revoking_invalidates_a_token_issued_before_it(
        self, service: AuthService, user_repo: FakeUserRepository
    ) -> None:
        user = user_repo.seed(_make_user())
        token = await service.login("iyad@example.com", "old-password")

        await service.revoke_all_sessions(user.id)

        with pytest.raises(InvalidToken):
            await service.get_current_user(token)

    async def test_token_issued_after_revocation_still_works(
        self, service: AuthService, user_repo: FakeUserRepository, cache: FakeCache
    ) -> None:
        # Set a cutoff clearly in the past rather than calling revoke_all_sessions()
        # right before login() -- both use real wall-clock time, and JWT's `iat`
        # only has whole-second precision, so racing the two real-time calls
        # against each other would make this test's outcome depend on whether
        # they land in the same second.
        user = user_repo.seed(_make_user())
        old_cutoff = int(datetime.now(timezone.utc).timestamp()) - 10
        await cache.set(f"token_valid_after:{user.id}", str(old_cutoff))

        token = await service.login("iyad@example.com", "old-password")
        current = await service.get_current_user(token)

        assert current.id == user.id

    async def test_revoking_one_user_does_not_affect_another(
        self, service: AuthService, user_repo: FakeUserRepository
    ) -> None:
        user_a = user_repo.seed(_make_user(email="a@example.com"))
        user_b = user_repo.seed(_make_user(email="b@example.com"))
        token_a = await service.login("a@example.com", "old-password")
        token_b = await service.login("b@example.com", "old-password")

        await service.revoke_all_sessions(user_a.id)

        with pytest.raises(InvalidToken):
            await service.get_current_user(token_a)
        current_b = await service.get_current_user(token_b)
        assert current_b.id == user_b.id

    async def test_revocation_is_checked_even_when_user_is_cached(
        self, service: AuthService, user_repo: FakeUserRepository
    ) -> None:
        user = user_repo.seed(_make_user())
        token = await service.login("iyad@example.com", "old-password")

        await service.get_current_user(token)  # warm the UserRead cache

        await service.revoke_all_sessions(user.id)

        with pytest.raises(InvalidToken):
            await service.get_current_user(token)


class TestPasswordReset:
    async def test_full_round_trip_changes_the_password(
        self, service: AuthService, user_repo: FakeUserRepository
    ) -> None:
        user = user_repo.seed(_make_user())

        raw_token = await service.request_password_reset(user.email)
        assert raw_token is not None

        await service.reset_password(raw_token, "new-password123")

        assert verify_password("new-password123", user.password)
        assert not verify_password("old-password", user.password)

    async def test_unknown_email_returns_none_and_creates_no_token(
        self, service: AuthService, reset_token_repo: FakePasswordResetTokenRepository
    ) -> None:
        result = await service.request_password_reset("nobody@example.com")
        assert result is None
        assert reset_token_repo._tokens == {}

    async def test_reusing_a_token_fails_the_second_time(
        self, service: AuthService, user_repo: FakeUserRepository
    ) -> None:
        user = user_repo.seed(_make_user())
        raw_token = await service.request_password_reset(user.email)
        assert raw_token is not None

        await service.reset_password(raw_token, "new-password123")

        with pytest.raises(InvalidToken):
            await service.reset_password(raw_token, "another-password456")

    async def test_expired_token_is_rejected(
        self,
        service: AuthService,
        user_repo: FakeUserRepository,
        reset_token_repo: FakePasswordResetTokenRepository,
    ) -> None:
        user = user_repo.seed(_make_user())
        raw_token = "a-known-raw-token-for-this-test"
        await reset_token_repo.create(
            PasswordResetTokenModel(
                user_id=user.id,
                token_hash=_hash_token(raw_token),
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )

        with pytest.raises(InvalidToken):
            await service.reset_password(raw_token, "new-password123")

    async def test_bad_token_is_rejected(self, service: AuthService) -> None:
        with pytest.raises(InvalidToken):
            await service.reset_password("not-a-real-token", "new-password123")

    async def test_resetting_password_invalidates_existing_tokens(
        self, service: AuthService, user_repo: FakeUserRepository
    ) -> None:
        user = user_repo.seed(_make_user())
        old_token = await service.login("iyad@example.com", "old-password")

        raw_token = await service.request_password_reset(user.email)
        assert raw_token is not None
        await service.reset_password(raw_token, "new-password123")

        with pytest.raises(InvalidToken):
            await service.get_current_user(old_token)
