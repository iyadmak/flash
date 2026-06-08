"""Configuration File"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings"""

    model_config = SettingsConfigDict(env_file=".env")
    app_name: str = "Flash"
    debug: bool = False


settings = Settings()
