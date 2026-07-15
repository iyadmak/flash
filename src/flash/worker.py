from arq.connections import RedisSettings
from flash.core.config import get_settings
from flash.tasks import send_password_reset_email


class WorkerSettings:
    functions = [send_password_reset_email]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
