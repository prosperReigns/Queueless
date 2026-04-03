"""FastAPI application entrypoint."""

from collections.abc import Awaitable, Callable
import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.api_response import error_response, success_response
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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log basic request details and response status."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid.uuid4())
        incoming_request_id = request.headers.get("X-Request-ID")
        if incoming_request_id:
            candidate = incoming_request_id.strip()
            if candidate and len(candidate) <= 64:
                try:
                    request_id = str(uuid.UUID(candidate))
                except ValueError:
                    logger.warning("Invalid X-Request-ID header received; generated a new request ID.")
        request.state.request_id = request_id

        logger.info(
            "request.started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request.completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )
        return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)
app.add_middleware(RequestUserMiddleware)
app.add_middleware(RequestLoggingMiddleware)
ensure_redis_storage_connectivity()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return standardized payload for FastAPI HTTP exceptions."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            error=str(exc.detail),
            code="HTTP_ERROR",
            request_id=request_id,
        ),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return standardized payload for request validation failures."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content=error_response(
            error="Request validation failed.",
            code="VALIDATION_ERROR",
            details=exc.errors(),
            request_id=request_id,
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return standardized payload for unhandled server errors."""
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        "Unhandled exception while processing request.",
        extra={
            "request_id": request_id,
            "error_type": exc.__class__.__name__,
        },
    )
    return JSONResponse(
        status_code=500,
        content=error_response(
            error="Internal server error.",
            code="INTERNAL_SERVER_ERROR",
            request_id=request_id,
        ),
    )


@app.get("/health")
async def health_check() -> dict:
    """Simple health check endpoint."""
    return success_response(data={"status": "ok"}, message="healthy")


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
