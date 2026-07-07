import jwt
from typing import Protocol

from flash.core.exceptions import InvalidCredentials, InvalidToken
from flash.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    decode_access_token,
)
from flash.models.user_model import UserModel

# compute at import time to have the same amount of time as a real password check
# so wrong password and wrong email can't be told apart by response time
_DUMMY_HASH = hash_password("dummy-password-for-timing-safety")


class AuthRepositoryProtocol(Protocol):
    async def get(self, id: int) -> UserModel | None: ...
    async def get_by_email(self, email: str) -> UserModel | None: ...


class AuthService:
    def __init__(self, repo: AuthRepositoryProtocol) -> None:
        self._repo = repo

    async def login(self, email: str, password: str) -> str:
        user = await self._repo.get_by_email(email)
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentials()
        if not verify_password(password, user.password):
            raise InvalidCredentials()
        return create_access_token(subject=str(user.id))

    async def get_current_user(self, token: str) -> UserModel:
        try:
            user_id = decode_access_token(token)
        except jwt.PyJWTError:
            raise InvalidToken() from None
        user = await self._repo.get(int(user_id))
        if user is None or not user.is_active:
            raise InvalidToken()
        return user
