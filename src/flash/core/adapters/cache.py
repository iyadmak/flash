import redis.asyncio as redis
from typing import Protocol, Any
from collections.abc import Awaitable
from functools import lru_cache
from flash.core.config import get_settings


class CacheProtocol(Protocol):
    def get(self, name: str, /) -> Awaitable[str | bytes | None]: ...
    def set(self, name: str, value: str, ex: int | None = None) -> Awaitable[Any]: ...
    def delete(self, *names: str) -> Awaitable[Any]: ...


@lru_cache
def get_user_cache() -> CacheProtocol:
    """Cache dependency: real Redis in the app. Overridden to a fake in tests."""
    return redis.Redis.from_url(get_settings().redis_url)
