from typing import Any, Protocol
from arq import create_pool
from arq.connections import RedisSettings
from flash.core.config import get_settings


class TasksQueueProtocol(Protocol):
    async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> Any: ...


_pool: TasksQueueProtocol | None = None


async def get_task_queue() -> TasksQueueProtocol:
    """Enqueue dependency: real arq pool in the app. Overridden to a fake in tests."""
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool
