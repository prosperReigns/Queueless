"""Branch-scoped kitchen display, ticket transitions and realtime event replay."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_active_user, get_db
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.branch import Branch
from app.models.business_membership import BusinessRole
from app.models.kitchen import KitchenEvent, KitchenTicket, KitchenTicketStatus
from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from app.services.business_service import get_membership
from app.services.kitchen_service import transition_kitchen_ticket

router = APIRouter(tags=["kitchen"])
_KITCHEN_ROLES = {
    BusinessRole.OWNER,
    BusinessRole.FRANCHISE_ADMIN,
    BusinessRole.BRANCH_MANAGER,
    BusinessRole.KITCHEN_STAFF,
}


class KitchenTicketStatusUpdate(BaseModel):
    status: KitchenTicketStatus


def _require_kitchen_access(db: Session, user: User, branch: Branch) -> None:
    if user.role == UserRole.ADMIN:
        return
    membership = get_membership(db, user.id, branch.business_id, branch.id)
    if membership is None or membership.role not in _KITCHEN_ROLES:
        raise HTTPException(status_code=403, detail="Kitchen access denied for this branch.")


def _ticket_payload(ticket: KitchenTicket) -> dict:
    order = ticket.order
    return {
        "ticket_id": ticket.id,
        "order_id": order.id,
        "branch_id": str(ticket.branch_id),
        "status": str(ticket.status),
        "order_source": order.order_source.value if order.order_source else None,
        "fulfillment_method": order.fulfillment_method.value if order.fulfillment_method else None,
        "scheduled_for": order.scheduled_for.isoformat() if order.scheduled_for else None,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "total_amount": str(order.total_amount),
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "accepted_at": ticket.accepted_at.isoformat() if ticket.accepted_at else None,
        "preparing_at": ticket.preparing_at.isoformat() if ticket.preparing_at else None,
        "ready_at": ticket.ready_at.isoformat() if ticket.ready_at else None,
        "items": [
            {"item_name": item.item_name, "quantity": item.quantity, "unit_price": str(item.price)}
            for item in order.items
        ],
    }


def _event_payload(event: KitchenEvent) -> dict:
    return {
        "id": event.id,
        "branch_id": str(event.branch_id),
        "ticket_id": event.ticket_id,
        "type": event.event_type,
        "payload": event.event_payload,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.get("/branches/{branch_id}/kitchen/queue")
def get_kitchen_queue(
    branch_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Return the persisted kitchen queue for one authorized branch."""
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found.")
    _require_kitchen_access(db, user, branch)
    stmt = (
        select(KitchenTicket)
        .options(selectinload(KitchenTicket.order).selectinload(Order.items))
        .where(KitchenTicket.branch_id == branch_id)
        .order_by(KitchenTicket.created_at.asc(), KitchenTicket.id.asc())
    )
    tickets = db.scalars(stmt).all()
    return {"branch_id": str(branch_id), "tickets": [_ticket_payload(ticket) for ticket in tickets]}


@router.patch("/kitchen/tickets/{ticket_id}/status")
def update_kitchen_ticket_status(
    ticket_id: int,
    payload: KitchenTicketStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Advance a paid order's kitchen ticket through its legal lifecycle."""
    ticket = db.scalar(
        select(KitchenTicket)
        .options(selectinload(KitchenTicket.order).selectinload(Order.items))
        .where(KitchenTicket.id == ticket_id)
        .with_for_update()
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Kitchen ticket not found.")
    branch = db.get(Branch, ticket.branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found.")
    _require_kitchen_access(db, user, branch)
    if ticket.order.status != OrderStatus.PAID:
        raise HTTPException(status_code=409, detail="Only provider-verified paid orders can enter kitchen processing.")
    try:
        updated = transition_kitchen_ticket(db, ticket, payload.status, actor_user_id=str(user.id))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _ticket_payload(updated)


@router.get("/branches/{branch_id}/kitchen/events")
def get_kitchen_events(
    branch_id: uuid.UUID,
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Polling fallback and replay API for durable branch kitchen events."""
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found.")
    _require_kitchen_access(db, user, branch)
    events = db.scalars(
        select(KitchenEvent)
        .where(KitchenEvent.branch_id == branch_id, KitchenEvent.id > after_id)
        .order_by(KitchenEvent.id.asc())
        .limit(limit)
    ).all()
    return {"events": [_event_payload(event) for event in events], "next_after_id": events[-1].id if events else after_id}


@router.websocket("/ws/kitchen/{branch_id}")
async def kitchen_events_websocket(
    websocket: WebSocket,
    branch_id: uuid.UUID,
    token: str = Query(min_length=1),
    after_id: int = Query(default=0, ge=0),
) -> None:
    """Stream durable events for an authorized branch; reconnect with after_id to replay."""
    try:
        claims = decode_token(token)
        if claims.get("type") != "access":
            raise ValueError("Invalid token type.")
        user_id = uuid.UUID(str(claims.get("sub")))
    except (ValueError, TypeError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    with SessionLocal() as db:
        user = db.get(User, user_id)
        branch = db.get(Branch, branch_id)
        if user is None or not user.is_active or branch is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        try:
            _require_kitchen_access(db, user, branch)
        except HTTPException:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await websocket.accept()
    cursor = after_id
    try:
        while True:
            with SessionLocal() as db:
                user = db.get(User, user_id)
                branch = db.get(Branch, branch_id)
                if user is None or not user.is_active or branch is None:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
                try:
                    _require_kitchen_access(db, user, branch)
                except HTTPException:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
                events = db.scalars(
                    select(KitchenEvent)
                    .where(KitchenEvent.branch_id == branch_id, KitchenEvent.id > cursor)
                    .order_by(KitchenEvent.id.asc())
                    .limit(100)
                ).all()
                payloads = [_event_payload(event) for event in events]
            for item in payloads:
                await websocket.send_json(item)
                cursor = item["id"]
            if not payloads:
                await asyncio.sleep(1)
    except (WebSocketDisconnect, RuntimeError):
        return
