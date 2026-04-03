"""Pytest fixtures for isolated backend API tests."""

from __future__ import annotations

import os
import sys
import types
from collections.abc import Generator
from typing import Dict

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure required env vars exist before importing app modules.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET_KEY", "01234567890123456789012345678901")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "test_paystack_secret")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Stub task modules to avoid Celery/Firebase side-effect dependencies in tests.
notifications_stub = types.ModuleType("app.tasks.notifications")
notifications_stub.queue_order_notification = lambda _order_id, _event: None
sys.modules.setdefault("app.tasks.notifications", notifications_stub)

orders_stub = types.ModuleType("app.tasks.orders")
orders_stub.schedule_order_expiry = lambda _order_id: None
sys.modules.setdefault("app.tasks.orders", orders_stub)

payments_stub = types.ModuleType("app.tasks.payments")
payments_stub.schedule_payment_verification_fallback = lambda _ref: None
sys.modules.setdefault("app.tasks.payments", payments_stub)

from app.api import deps
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.db import session as db_session
from app.db.base import Base
import app.models  # noqa: F401  # Ensure ORM models are registered in metadata.


@pytest.fixture(scope="session")
def test_engine():
    """Create a dedicated in-memory database engine for tests."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session_fixture(test_engine) -> Generator[Session, None, None]:
    """Provide a clean transactional database session per test."""
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session_fixture: Session, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Create FastAPI TestClient with DB and side-effect dependencies isolated."""

    # Route all DB usage to the test session.
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session_fixture

    app = FastAPI(title="Queueless API Test")
    limiter.enabled = False
    app.state.limiter = limiter
    app.add_exception_handler(Exception, lambda req, exc: (_ for _ in ()).throw(exc))
    from slowapi.errors import RateLimitExceeded

    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.include_router(api_router, prefix=get_settings().API_V1_PREFIX)

    app.dependency_overrides[deps.get_db] = override_get_db

    monkeypatch.setattr(db_session, "SessionLocal", lambda: db_session_fixture)

    monkeypatch.setattr("app.services.auth_service.get_password_hash", lambda raw: f"hashed::{raw}")
    monkeypatch.setattr(
        "app.services.auth_service.verify_password",
        lambda raw, hashed: hashed == f"hashed::{raw}",
    )

    monkeypatch.setattr("app.services.order_service.publish_merchant_new_order", lambda _merchant_id, _order: None)
    monkeypatch.setattr("app.services.order_service.publish_customer_status_update", lambda _customer_id, _order: None)

    class _MockResponse:
        status_code = 200

        @staticmethod
        def json() -> Dict[str, object]:
            return {
                "status": True,
                "data": {
                    "authorization_url": "https://paystack.test/authorize",
                    "access_code": "test_access_code",
                    "reference": "provider-test-reference",
                },
            }

        text = "ok"

    monkeypatch.setattr("app.services.payment_service.httpx.post", lambda *args, **kwargs: _MockResponse())

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
