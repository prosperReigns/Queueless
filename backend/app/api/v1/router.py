"""Main API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, orders, payments, products, qr_codes, stores, websocket

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(stores.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)
api_router.include_router(qr_codes.router)
api_router.include_router(payments.router)
api_router.include_router(websocket.router)
