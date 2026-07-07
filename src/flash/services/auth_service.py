from typing import Protocol

from flash.core.exceptions import InvalidCredentials
from flash.core.security import create_access_token, hash_password, verify_password
from flash.models.user_model import UserModel

# compute at import time to have the same amount of time as a real password check
# so wrong password and wrong email can't be told apart by response time
_DUMMY_HASH = hash_password("dummy-password-for-timing-safety")


class AuthRepositoryProtocol(Protocol):
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
