"""WebSocket endpoints for real-time order notifications."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import decode_token
from app.models.user import UserRole
from app.services.auth_service import get_user_by_id
from app.services.websocket_service import connection_manager

router = APIRouter(tags=["websocket"])
_WS_RECEIVE_TIMEOUT_SECONDS = 60


@router.websocket("/ws/orders")
async def order_notifications_websocket(
    websocket: WebSocket,
    token: str = Query(min_length=1),
) -> None:
    """Subscribe authenticated customers/merchants to order event notifications."""
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

    db: Session = SessionLocal()
    user = None
    try:
        try:
            user = get_user_by_id(db, subject)
        except (ValueError, TypeError):
            pass
    finally:
        db.close()

    if user is None or not user.is_active:
        await websocket.close(code=close_code)
        return
    if user.role not in {UserRole.MERCHANT, UserRole.CUSTOMER}:
        await websocket.close(code=close_code)
        return

    await connection_manager.connect(websocket, user_id=user.id, role=user.role)
    try:
        try:
            while True:
                # Intentionally read and ignore client frames to keep this server-push socket alive.
                await asyncio.wait_for(websocket.receive(), timeout=_WS_RECEIVE_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            await websocket.close()
        except WebSocketDisconnect:
            pass
    finally:
        await connection_manager.disconnect(websocket, user_id=user.id, role=user.role)
