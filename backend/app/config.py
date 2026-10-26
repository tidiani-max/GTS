"""Environment-based configuration with validation (fails fast on unsafe production values)."""
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRETS = {"", "change-me", "changeme", "secret", "change-me-to-a-long-random-string"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://gst:gst@localhost:5432/gst"
    secret_key: str = "change-me"
    access_token_minutes: int = Field(15, ge=1, le=240)
    refresh_token_days: int = Field(7, ge=1, le=90)
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cors_origins: str = "http://localhost:8443,http://localhost:8080"
    trust_proxy_headers: bool = False

    # Rate limits: "max_requests/window_seconds"
    rate_limit_contact: str = "5/600"
    rate_limit_login: str = "10/300"
    rate_limit_enabled: bool = True

    # Email: console (log only) | smtp | disabled
    email_mode: Literal["console", "smtp", "disabled"] = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    email_from: str = "GST <no-reply@gst-demo.ml>"

    # Seed (demo only)
    seed_admin_email: str = "admin@gst-demo.ml"
    seed_admin_password: str = "ChangeMe!2025"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        if self.environment == "production":
            if self.secret_key in INSECURE_SECRETS or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be a random string of at least 32 characters in production")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production (serve over HTTPS)")
            if "*" in self.cors_origin_list:
                raise ValueError("CORS_ORIGINS must not contain '*' in production")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
        if self.email_mode == "smtp" and not self.smtp_host:
            raise ValueError("EMAIL_MODE=smtp requires SMTP_HOST")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
