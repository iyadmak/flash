import redis.asyncio as redis
from functools import lru_cache
from typing import Any, Protocol

from flash.core.config import get_settings


class LockProtocol(Protocol):
    def lock(
        self, name: str, *, timeout: float | None = None, blocking: bool = True
    ) -> Any: ...


@lru_cache
def get_lock_client() -> LockProtocol:
    """Distributed lock backend: real Redis in the app. Overridden to a fake in tests."""
    return redis.Redis.from_url(get_settings().redis_url)
