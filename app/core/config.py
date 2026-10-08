from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCALEPULSE_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "ScalePulse Gateway Core"
    version: str = "0.1.0"
    env: Literal["local", "dev", "staging", "prod"] = "local"
    log_level: str = "info"


@lru_cache
def get_settings() -> Settings:
    return Settings()
