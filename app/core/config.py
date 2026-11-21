"""Application settings, loaded from environment variables and an optional .env file."""
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Tasks API"
    environment: str = "development"  # development | production | test
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./app.db"

    # MUST be >= 32 chars. Generate one: python -c "import secrets; print(secrets.token_urlsafe(48))"
    secret_key: str = "dev-only-secret-change-me-0123456789abcdef"
    access_token_minutes: int = Field(15, ge=1)
    refresh_token_days: int = Field(7, ge=1)
    bcrypt_rounds: int = Field(12, ge=4, le=16)

    # Explicit origins only. With allow_credentials=True browsers reject "*" anyway.
    # In .env use JSON: CORS_ORIGINS=["http://localhost:3000"]
    cors_origins: list[str] = ["http://localhost:3000"]

    # Optional: create this admin on startup if it does not exist yet.
    first_admin_email: str | None = None
    first_admin_password: str | None = None

    @field_validator("secret_key")
    @classmethod
    def _secret_long_enough(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("cors_origins")
    @classmethod
    def _no_wildcard(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError("CORS_ORIGINS must list explicit origins, not '*'")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
