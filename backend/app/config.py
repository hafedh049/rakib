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

    # Signs public complaint-tracking + satisfaction links. Deliberately a different
    # secret from jwt_secret: a leaked tracking link must never become a session.
    tracking_token_secret: str = "change-me-too"
    tracking_token_ttl_days: int = 365

    triage_backend: Literal["ml", "rules", "llm"] = "ml"
    ml_artifacts_dir: str = "./ml_artifacts"
    category_confidence_threshold: float = 0.55
    ambiguity_margin: float = 0.15
    dedup_auto_threshold: float = 0.82
    dedup_suggest_threshold: float = 0.65
    dedup_cross_claimant_threshold: float = 0.90
    retrain_min_samples: int = 200
    retrain_correction_trigger: int = 50
    retrain_f1_tolerance: float = 0.02

    sla_business_hours: bool = False
    sla_timezone: str = "Africa/Tunis"
    sla_hours_p1: int = 4
    sla_hours_p2: int = 24
    sla_hours_p3: int = 72
    sla_hours_p4: int = 168

    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "reclamations"
    s3_access_key: str = "rakib"
    s3_secret_key: str = "rakib-dev-secret"
    s3_region: str = "us-east-1"
    max_attachment_mb: int = 10

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True

    frontend_url: str = "http://localhost:5173"
    public_url: str = "http://localhost:5173"

    openrouter_api_key: str = ""

    @property
    def sla_hours_by_priority(self) -> dict[int, int]:
        return {
            1: self.sla_hours_p1,
            2: self.sla_hours_p2,
            3: self.sla_hours_p3,
            4: self.sla_hours_p4,
        }

    @property
    def mail_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
