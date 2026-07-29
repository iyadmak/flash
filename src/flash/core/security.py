import asyncio
import jwt
from concurrent.futures import ThreadPoolExecutor
from typing import cast, NamedTuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime, timedelta, timezone
from flash.core.config import get_settings

_hasher = PasswordHasher()


class TokenPayload(NamedTuple):
    sub: str
    iat: datetime


def create_access_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": subject, "iat": now, "exp": expire},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> TokenPayload:
    settings = get_settings()
    payload = jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
    return TokenPayload(
        sub=cast(str, payload["sub"]),
        iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
    )


# Argon2 is deliberately expensive: ~35ms of CPU and 64 MiB per call. On the event
# loop it blocks every other request in the process, so the async wrappers below are
# what request paths must use. The `_blocking` names are the escape hatch for import
# time and test setup, where there is no loop to stall.
#
# A dedicated, small pool rather than asyncio.to_thread. to_thread shares the default
# executor, which allows cpu_count + 4 workers -- 12 concurrent hashes means 768 MiB
# of randomly-accessed memory, which saturates memory bandwidth and makes each hash
# several times slower than running them one at a time. Bounding concurrency also
# caps how much memory a burst of logins can claim, and keeps hashing from starving
# the default executor that serves sync route handlers.
_hashing_pool = ThreadPoolExecutor(
    max_workers=get_settings().password_hashing_threads,
    thread_name_prefix="argon2",
)


def hash_password_blocking(password: str) -> str:
    return _hasher.hash(password)


def verify_password_blocking(password: str, hashed_password: str) -> bool:
    try:
        return _hasher.verify(hashed_password, password)
    except VerifyMismatchError:
        return False


async def hash_password(password: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_hashing_pool, hash_password_blocking, password)


async def verify_password(password: str, hashed_password: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _hashing_pool, verify_password_blocking, password, hashed_password
    )
