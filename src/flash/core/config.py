"""Configuration File"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings"""

    # ------- app config -------
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    app_name: str = "Flash"
    debug: bool = False
    log_level: str = "INFO"
    # ------- infrastructure config -------
    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    # False by default: pgbouncer already hands out live connections, so pre-ping
    # only adds a round trip to every checkout. pool_recycle covers staleness.
    db_pool_pre_ping: bool = False
    real_database_url: str
    mongodb_url: str
    redis_url: str
    rabbitmq_url: str
    kafka_bootstrap_servers: str
    # ------- auth config -------
    secret_key: str
    jwt_algorithm: str = "HS256"
    # Argon2 costs 64 MiB per call, so concurrency here is a memory budget, not a
    # CPU one: too many at once saturates memory bandwidth and slows every hash.
    password_hashing_threads: int = 2
    access_token_expire_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
