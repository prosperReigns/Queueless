"""Main API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, orders, payments, products, stores

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(stores.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
