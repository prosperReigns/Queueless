"""API endpoint modules."""

from app.api.v1.endpoints import auth
from app.api.v1.endpoints import orders
from app.api.v1.endpoints import products
from app.api.v1.endpoints import stores

__all__ = ["auth", "stores", "products", "orders"]
