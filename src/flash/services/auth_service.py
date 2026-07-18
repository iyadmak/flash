import jwt
import hashlib
import secrets
from typing import Protocol
from datetime import datetime, timedelta, timezone

from flash.core.exceptions import InvalidCredentials, InvalidToken
from flash.core.cache import CacheProtocol
from flash.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    decode_access_token,
)
from flash.celery_tasks import send_password_reset_email_celery
from flash.models import UserModel, PasswordResetTokenModel
from flash.schemas.user_schema import UserRead
from flash.core.config import get_settings

USER_CACHE_TTL_SECONDS = 300

# compute at import time to have the same amount of time as a real password check
# so wrong password and wrong email can't be told apart by response time
_DUMMY_HASH = hash_password("dummy-password-for-timing-safety")

RESET_TOKEN_EXPIRE_MINUTES = 30


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthRepositoryProtocol(Protocol):
    async def get(self, id: int) -> UserModel | None: ...
    async def get_by_email(self, email: str) -> UserModel | None: ...


class PasswordResetRepositoryProtocol(Protocol):
    async def create(
        self, instance: PasswordResetTokenModel
    ) -> PasswordResetTokenModel: ...
    async def get_by_token_hash(
        self, token_hash: str
    ) -> PasswordResetTokenModel | None: ...
    async def commit(self) -> None: ...


class AuthService:
    def __init__(
        self,
        user_repo: AuthRepositoryProtocol,
        reset_token_repo: PasswordResetRepositoryProtocol,
        cache: CacheProtocol,
    ) -> None:
        self._user_repo = user_repo
        self._reset_token_repo = reset_token_repo
        self._cache = cache

    async def login(self, email: str, password: str) -> str:
        user = await self._user_repo.get_by_email(email)
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentials()
        if not verify_password(password, user.password):
            raise InvalidCredentials()
        return create_access_token(subject=str(user.id))

    async def get_current_user(self, token: str) -> UserRead:
        try:
            payload = decode_access_token(token)
        except jwt.PyJWTError:
            raise InvalidToken() from None
        valid_after = await self._cache.get(f"token_valid_after:{payload.sub}")
        if valid_after is not None and payload.iat.timestamp() <= float(valid_after):
            raise InvalidToken()
        cached_user = await self._cache.get(f"user:{payload.sub}")
        if cached_user is not None:
            user = UserRead.model_validate_json(cached_user)
            if not user.is_active:
                raise InvalidToken()
            return user
        db_user = await self._user_repo.get(int(payload.sub))
        if db_user is None or not db_user.is_active:
            raise InvalidToken()
        user = UserRead.model_validate(db_user)
        await self._cache.set(
            f"user:{payload.sub}", user.model_dump_json(), ex=USER_CACHE_TTL_SECONDS
        )
        return user

    async def revoke_all_sessions(self, user_id: int) -> None:
        now = int(datetime.now(timezone.utc).timestamp())
        await self._cache.set(
            f"token_valid_after:{user_id}",
            str(now),
            ex=get_settings().access_token_expire_minutes * 60,
        )

    async def request_password_reset(self, email: str) -> str | None:
        user = await self._user_repo.get_by_email(email)
        if user is None:
            return None
        raw_token = secrets.token_urlsafe(32)
        reset_token = PasswordResetTokenModel(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
        )
        await self._reset_token_repo.create(reset_token)
        await self._reset_token_repo.commit()
        send_password_reset_email_celery.delay(email, raw_token)
        return raw_token

    async def reset_password(self, token: str, new_password: str) -> None:
        reset_token = await self._reset_token_repo.get_by_token_hash(_hash_token(token))
        if reset_token is None or reset_token.used_at is not None:
            raise InvalidToken()
        if reset_token.expires_at < datetime.now(timezone.utc):
            raise InvalidToken()
        user = await self._user_repo.get(reset_token.user_id)
        if user is None:
            raise InvalidToken()
        user.password = hash_password(new_password)
        reset_token.used_at = datetime.now(timezone.utc)
        await self._reset_token_repo.commit()
        await self.revoke_all_sessions(user.id)
