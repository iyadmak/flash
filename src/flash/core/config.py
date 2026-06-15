"""Configuration File"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    app_name: str = "Flash"
    debug: bool = False
    log_level: str = "INFO"
    database_url: str
    # secret_key: str


@lru_cache
def get_settings() -> Settings:
    """Get Settings"""
    return Settings()
