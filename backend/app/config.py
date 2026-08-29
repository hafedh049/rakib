from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Rakib"
    environment: Literal["development", "staging", "production", "test"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    mongo_uri: str = "mongodb://localhost:27017/reclamations"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7

    # Signs the public complaint-tracking links. Deliberately a different secret
    # from jwt_secret: a leaked tracking link must never become a session.
    tracking_token_secret: str = "change-me-too"
    tracking_token_ttl_days: int = 365

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True

    frontend_url: str = "http://localhost:5173"
    public_url: str = "http://localhost:5173"

    @property
    def mail_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
