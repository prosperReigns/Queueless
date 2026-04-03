"""FastAPI application entrypoint."""

from collections.abc import Awaitable, Callable
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limiter import (
    ensure_redis_storage_connectivity,
    limiter,
    rate_limit_exceeded_handler,
)
from app.db.session import SessionLocal
from app.services.auth_service import get_user_by_id
from app.core.security import decode_token

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title=settings.APP_NAME)


class RequestUserMiddleware(BaseHTTPMiddleware):
    """Attach authenticated user to request state for middleware/decorators."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.user = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            try:
                payload = decode_token(token)
            except ValueError:
                logger.warning("Failed to decode bearer token.", exc_info=True)
                return await call_next(request)

            sub = payload.get("sub")
            if isinstance(sub, str):
                try:
                    user_id = uuid.UUID(sub)
                except ValueError:
                    logger.warning("Failed to parse bearer token subject as UUID.", exc_info=True)
                    return await call_next(request)
                try:
                    with SessionLocal() as db:
                        request.state.user = get_user_by_id(db, user_id)
                except SQLAlchemyError:
                    logger.warning("Failed to load authenticated user from database.", exc_info=True)
                    request.state.user = None
        return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)
app.add_middleware(RequestUserMiddleware)
ensure_redis_storage_connectivity()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
