"""API endpoint modules."""

from app.api.v1.endpoints import auth
from app.api.v1.endpoints import admin
from app.api.v1.endpoints import notifications
from app.api.v1.endpoints import orders
from app.api.v1.endpoints import payments
from app.api.v1.endpoints import products
from app.api.v1.endpoints import qr_codes
from app.api.v1.endpoints import stores
from app.api.v1.endpoints import websocket

__all__ = [
    "auth",
    "admin",
    "notifications",
    "stores",
    "products",
    "orders",
    "qr_codes",
    "payments",
    "websocket",
]
