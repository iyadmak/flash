from functools import lru_cache
from typing import Annotated, Any, Callable, Coroutine

from fastapi import Depends, Request
from limits import RateLimitItem, parse
from limits.aio.storage import RedisStorage, Storage
from limits.aio.strategies import FixedWindowRateLimiter
from flash.core.config import get_settings
from flash.core.exceptions import RateLimitExceeded


@lru_cache
def get_rate_limit_storage() -> Storage:
    """Storage dependency: real Redis in the app. Overridden to in-memory in tests."""
    return RedisStorage(get_settings().redis_url, implementation="redispy")


def rate_limit(
    limit_string: str,
) -> Callable[[Request, Storage], Coroutine[Any, Any, None]]:
    """Dependecy factory: Depends(rate_limit("5/minute"))"""
    item: RateLimitItem = parse(limit_string)

    async def check_rate_limit(
        request: Request,
        storage: Annotated[Storage, Depends(get_rate_limit_storage)],
    ) -> None:
        client_ip = request.client.host if request.client else "unknown"
        strategy = FixedWindowRateLimiter(storage)
        if not await strategy.hit(item, client_ip):
            raise RateLimitExceeded()

    return check_rate_limit
