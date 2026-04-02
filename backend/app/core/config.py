"""Application configuration."""

from functools import lru_cache

from pydantic import Field, ValidationInfo
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    APP_NAME: str = "Queueless API"
    API_V1_PREFIX: str = "/api/v1"
    JWT_SECRET_KEY: str = Field(..., min_length=32, description="Signing key for JWT tokens")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    DATABASE_URL: str = Field(
        ...,
        description="Required PostgreSQL SQLAlchemy URL, e.g. postgresql+psycopg2://user:pass@host:5432/db",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    PAYSTACK_SECRET_KEY: str | None = Field(
        default=None,
        description="Paystack secret key used for transaction initialization and webhook verification",
    )
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None
    CELERY_TASK_ALWAYS_EAGER: bool = False
    ORDER_EXPIRY_MINUTES: int = Field(default=10, ge=1, le=1440)

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Ensure SQLAlchemy URL uses a PostgreSQL scheme."""
        allowed_prefixes = ("postgresql://", "postgresql+", "postgres://")
        if not value.startswith(allowed_prefixes):
            raise ValueError("DATABASE_URL must use a PostgreSQL scheme")
        return value

    @field_validator("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def default_celery_redis_urls(cls, value: str | None, info: ValidationInfo) -> str | None:
        """Fallback Celery broker/backend URLs to REDIS_URL when not provided."""
        if value:
            return value
        redis_url = info.data.get("REDIS_URL") if info.data else None
        if isinstance(redis_url, str) and redis_url:
            return redis_url
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
