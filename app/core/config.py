from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
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
    database_url: str | None = None
    admin_token: SecretStr | None = None
    redis_url: str | None = None
    rate_limit_enabled: bool = True
    api_key_pepper: SecretStr | None = None

    @field_validator("admin_token")
    @classmethod
    def validate_admin_token(cls, token: SecretStr | None) -> SecretStr | None:
        if token is not None:
            value = token.get_secret_value()
            if value and len(value) < 32:
                raise ValueError("admin token must contain at least 32 characters")
        return token

    @field_validator("api_key_pepper")
    @classmethod
    def validate_api_key_pepper(cls, pepper: SecretStr | None) -> SecretStr | None:
        if pepper is not None:
            value = pepper.get_secret_value()
            if value and len(value) < 32:
                raise ValueError("API key pepper must contain at least 32 characters")
        return pepper


@lru_cache
def get_settings() -> Settings:
    return Settings()
