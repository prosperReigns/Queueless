"""SQLAlchemy declarative base and model imports."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


# Import models so metadata is populated for migrations/autogeneration.
from app.models import order, order_item, payment, product, store, user  # noqa: E402,F401
