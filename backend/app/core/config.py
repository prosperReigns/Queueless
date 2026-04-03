"""Application configuration."""

from functools import lru_cache

from pydantic import Field, field_validator
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
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_HEADERS: list[str] = ["Authorization", "Content-Type", "Accept", "Origin"]
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
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
    RATE_LIMIT_AUTH: str = "20/minute"
    RATE_LIMIT_ORDER_CREATE: str = "10/minute"
    RATE_LIMIT_PAYMENTS: str = "20/minute"
    RATE_LIMIT_PAYMENT_WEBHOOK: str = "300/minute"
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None
    CELERY_TASK_ALWAYS_EAGER: bool = False
    FIREBASE_CREDENTIALS_JSON: str | None = None
    FIREBASE_CREDENTIALS_PATH: str | None = None
    TERMII_API_KEY: str | None = None
    TERMII_BASE_URL: str = "https://api.ng.termii.com"  # Override for other Termii regions.
    TERMII_SENDER_ID: str = "Queueless"
    TERMII_CHANNEL: str = "generic"
    TERMII_SEND_ORDER_READY_SMS: bool = False
    TERMII_TIMEOUT_SECONDS: int = Field(default=10, ge=1, le=60)
    ORDER_EXPIRY_MINUTES: int = Field(
        default=10,
        ge=1,
        le=1440,
        description="Unpaid order validity window before automatic cancellation (1-1440 minutes).",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Ensure SQLAlchemy URL uses a PostgreSQL scheme."""
        allowed_prefixes = ("postgresql://", "postgresql+", "postgres://")
        if not value.startswith(allowed_prefixes):
            raise ValueError("DATABASE_URL must use a PostgreSQL scheme")
        return value

@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
