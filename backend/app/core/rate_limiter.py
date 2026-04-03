"""Redis-backed rate limiter configuration."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from limits.storage import storage_from_string
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings


def _rate_limit_key_func(request: Request) -> str:
    """Build a stable client key using user id when available, else IP address."""
    user = getattr(request.state, "user", None)
    if user is not None and getattr(user, "id", None) is not None:
        return f"user:{user.id}"
    return get_remote_address(request)


def build_limiter() -> Limiter:
    """Create a slowapi Limiter backed by Redis."""
    settings = get_settings()
    return Limiter(
        key_func=_rate_limit_key_func,
        storage_uri=settings.REDIS_URL,
        strategy="fixed-window",
        headers_enabled=True,
    )


def ensure_redis_storage_connectivity() -> None:
    """Fail fast if Redis storage cannot be initialized."""
    settings = get_settings()
    storage = storage_from_string(settings.REDIS_URL)
    storage.check()


def rate_limit_exceeded_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return JSON error payload for rate-limit violations."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


limiter = build_limiter()
