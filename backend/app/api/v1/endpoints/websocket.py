"""WebSocket endpoints for real-time order notifications."""

from __future__ import annotations
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from app.db.session import SessionLocal
from app.core.security import decode_token
from app.models.user import UserRole
from app.services.auth_service import get_user_by_id
from app.services.websocket_service import connection_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/orders")
async def order_notifications_websocket(
    websocket: WebSocket,
    token: str = Query(min_length=1),
) -> None:
    """Subscribe authenticated users to role-scoped order event notifications."""
    close_code = status.WS_1008_POLICY_VIOLATION

    try:
        payload = decode_token(token)
    except (ValueError, JWTError):
        await websocket.close(code=close_code)
        return

    subject = payload.get("sub")
    token_type = payload.get("type")
    if subject is None or token_type != "access":
        await websocket.close(code=close_code)
        return
    try:
        user_id = uuid.UUID(str(subject))
    except (ValueError, TypeError):
        await websocket.close(code=close_code)
        return

    user = None
    with SessionLocal() as db:
        user = get_user_by_id(db, user_id)

    if user is None or not user.is_active:
        await websocket.close(code=close_code)
        return
    if user.role not in {UserRole.ADMIN, UserRole.MERCHANT, UserRole.CUSTOMER}:
        await websocket.close(code=close_code)
        return

    await connection_manager.connect(websocket, user_id=user.id, role=user.role)
    try:
        while True:
            # Read client frames to keep connection alive; only disconnect frames are acted upon.
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect(websocket, user_id=user.id, role=user.role)
