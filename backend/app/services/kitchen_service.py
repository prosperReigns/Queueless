"""Kitchen ticket lifecycle and durable event creation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.kitchen import KitchenEvent, KitchenTicket, KitchenTicketStatus
from app.models.order import Order, OrderStatus
from app.services.fulfillment_service import ensure_order_fulfillment, mark_fulfillment_ready


_ALLOWED_TRANSITIONS = {
    KitchenTicketStatus.NEW: {KitchenTicketStatus.ACCEPTED},
    KitchenTicketStatus.ACCEPTED: {KitchenTicketStatus.PREPARING},
    KitchenTicketStatus.PREPARING: {KitchenTicketStatus.READY},
    KitchenTicketStatus.READY: set(),
}


def validate_kitchen_transition(current_status, next_status) -> tuple[KitchenTicketStatus, KitchenTicketStatus]:
    """Validate the strict NEW → ACCEPTED → PREPARING → READY workflow."""
    try:
        current = KitchenTicketStatus(current_status)
        target = KitchenTicketStatus(next_status)
    except ValueError as exc:
        raise ValueError("Unknown kitchen ticket status.") from exc
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Invalid kitchen ticket transition: {current.value} -> {target.value}.")
    return current, target


def _record_event(db: Session, ticket: KitchenTicket, event_type: str, payload: dict) -> KitchenEvent:
    event = KitchenEvent(
        branch_id=ticket.branch_id,
        ticket_id=ticket.id,
        event_type=event_type,
        event_payload=payload,
    )
    db.add(event)
    return event


def ensure_kitchen_ticket(db: Session, order: Order, *, commit: bool = True) -> Optional[KitchenTicket]:
    """Create exactly one kitchen ticket for a verified-paid branch order."""
    if order.branch_id is None or order.status != OrderStatus.PAID:
        return None
    ticket = db.scalar(
        select(KitchenTicket).where(KitchenTicket.order_id == order.id).with_for_update()
    )
    if ticket is not None:
        return ticket

    ticket = KitchenTicket(
        order_id=order.id,
        branch_id=order.branch_id,
        status=KitchenTicketStatus.NEW.value,
    )
    db.add(ticket)
    db.flush()
    ensure_order_fulfillment(db, order)
    _record_event(
        db,
        ticket,
        "ticket.created",
        {"ticket_id": ticket.id, "order_id": order.id, "branch_id": str(order.branch_id), "status": KitchenTicketStatus.NEW.value},
    )
    if commit:
        db.commit()
        db.refresh(ticket)
    return ticket


def transition_kitchen_ticket(
    db: Session,
    ticket: KitchenTicket,
    next_status: KitchenTicketStatus,
    *,
    actor_user_id: str,
) -> KitchenTicket:
    """Apply a legal ticket transition and persist its event in one transaction."""
    current, target = validate_kitchen_transition(ticket.status, next_status)
    ticket.status = target.value
    now = datetime.now(timezone.utc)
    if target == KitchenTicketStatus.ACCEPTED:
        ticket.accepted_at = now
    elif target == KitchenTicketStatus.PREPARING:
        ticket.preparing_at = now
    elif target == KitchenTicketStatus.READY:
        ticket.ready_at = now
    db.add(ticket)
    if target == KitchenTicketStatus.READY:
        mark_fulfillment_ready(db, ticket.order)
    _record_event(
        db,
        ticket,
        f"ticket.{target.value}",
        {
            "ticket_id": ticket.id,
            "order_id": ticket.order_id,
            "branch_id": str(ticket.branch_id),
            "from_status": current.value,
            "status": target.value,
            "actor_user_id": actor_user_id,
        },
    )
    db.commit()
    db.refresh(ticket)
    return ticket
