"""Application configuration."""

from functools import lru_cache

from pydantic import Field
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
    DATABASE_URL: str = Field(
        ...,
        description="Required PostgreSQL SQLAlchemy URL, e.g. postgresql+psycopg2://user:pass@host:5432/db",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

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
