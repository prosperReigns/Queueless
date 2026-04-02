"""WebSocket connection and notification service."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime
import logging
import uuid
from typing import Any

import anyio
from fastapi import WebSocket, WebSocketDisconnect

from app.models.order import Order
from app.models.user import UserRole

logger = logging.getLogger(__name__)


def _serialize_order_payload(order: Order, event_type: str) -> dict[str, Any]:
    """Build a JSON-serializable order event payload."""
    created_at = order.created_at
    if isinstance(created_at, datetime):
        created_at_value = created_at.isoformat()
    else:
        created_at_value = None

    total_amount = order.total_amount
    total_amount_value = str(total_amount)

    return {
        "type": event_type,
        "order_id": order.id,
        "store_id": order.store_id,
        "customer_id": str(order.user_id),
        "status": order.status.value,
        "total_amount": total_amount_value,
        "created_at": created_at_value,
    }


class WebSocketConnectionManager:
    """Track and notify active merchant/customer websocket sessions."""

    def __init__(self) -> None:
        self._merchant_connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)
        self._customer_connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, *, user_id: uuid.UUID, role: UserRole) -> None:
        """Accept and register an authenticated websocket connection."""
        await websocket.accept()
        async with self._lock:
            if role == UserRole.MERCHANT:
                self._merchant_connections[user_id].add(websocket)
            elif role == UserRole.CUSTOMER:
                self._customer_connections[user_id].add(websocket)
            else:
                await websocket.close()

    async def disconnect(self, websocket: WebSocket, *, user_id: uuid.UUID, role: UserRole) -> None:
        """Remove a websocket connection from role-scoped tracking."""
        async with self._lock:
            if role == UserRole.MERCHANT:
                self._merchant_connections[user_id].discard(websocket)
                if not self._merchant_connections[user_id]:
                    del self._merchant_connections[user_id]
            elif role == UserRole.CUSTOMER:
                self._customer_connections[user_id].discard(websocket)
                if not self._customer_connections[user_id]:
                    del self._customer_connections[user_id]

    async def notify_merchant_new_order(self, merchant_id: uuid.UUID, order: Order) -> None:
        """Notify a merchant about a newly created order."""
        payload = _serialize_order_payload(order, "new_order")
        await self._broadcast(merchant_id=merchant_id, payload=payload)

    async def notify_customer_status_update(self, customer_id: uuid.UUID, order: Order) -> None:
        """Notify a customer about an order status change."""
        payload = _serialize_order_payload(order, "order_status_update")
        await self._broadcast(customer_id=customer_id, payload=payload)

    async def _broadcast(
        self,
        *,
        payload: dict[str, Any],
        merchant_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> None:
        """Send payload to all active sockets in a target channel."""
        if merchant_id is None and customer_id is None:
            return

        async with self._lock:
            if merchant_id is not None:
                sockets = list(self._merchant_connections.get(merchant_id, set()))
            elif customer_id is not None:
                sockets = list(self._customer_connections.get(customer_id, set()))

        disconnected: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except (RuntimeError, WebSocketDisconnect):
                disconnected.append(socket)

        if disconnected:
            async with self._lock:
                if merchant_id is not None:
                    bucket = self._merchant_connections.get(merchant_id, set())
                    for socket in disconnected:
                        bucket.discard(socket)
                    if not bucket and merchant_id in self._merchant_connections:
                        del self._merchant_connections[merchant_id]
                if customer_id is not None:
                    bucket = self._customer_connections.get(customer_id, set())
                    for socket in disconnected:
                        bucket.discard(socket)
                    if not bucket and customer_id in self._customer_connections:
                        del self._customer_connections[customer_id]


connection_manager = WebSocketConnectionManager()


def _dispatch_async(
    callback: Callable[..., Awaitable[None]],
    *args: Any,
) -> None:
    """Dispatch coroutine from either async context or AnyIO worker thread."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            anyio.from_thread.run(callback, *args)
        except RuntimeError:
            logger.warning("Unable to dispatch websocket notification from thread context.")
            return
        return
    loop.create_task(callback(*args))


def publish_merchant_new_order(merchant_id: uuid.UUID, order: Order) -> None:
    """Emit a real-time new-order event to merchant sockets."""
    _dispatch_async(connection_manager.notify_merchant_new_order, merchant_id, order)


def publish_customer_status_update(customer_id: uuid.UUID, order: Order) -> None:
    """Emit a real-time status-update event to customer sockets."""
    _dispatch_async(connection_manager.notify_customer_status_update, customer_id, order)
