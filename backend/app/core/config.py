from functools import lru_cache
import secrets

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AOV Strategy Open"
    app_env: str = "development"
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    database_url: str = "sqlite:///./aov_strategy.db"
    frontend_origin: str = "http://localhost:5173"
    rate_limit_per_minute: int = 120
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

