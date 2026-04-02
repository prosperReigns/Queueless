"""API endpoint modules."""

from app.api.v1.endpoints import auth
from app.api.v1.endpoints import orders
from app.api.v1.endpoints import payments
from app.api.v1.endpoints import products
from app.api.v1.endpoints import stores
from app.api.v1.endpoints import websocket

__all__ = ["auth", "stores", "products", "orders", "payments", "websocket"]
