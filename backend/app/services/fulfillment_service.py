"""Order collection credentials, fulfillment lifecycle and handoff."""
from __future__ import annotations
import hashlib, hmac, json, secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.fulfillment import CollectionCredential, CollectionCredentialStatus, FulfillmentEvent, FulfillmentStatus, OrderFulfillment
from app.models.kitchen import KitchenTicket, KitchenTicketStatus
from app.models.order import FulfillmentMethod, Order, OrderStatus

def _digest(value: str) -> str:
    # A server-side pepper prevents offline PIN guessing after a DB-only compromise.
    return hmac.new(get_settings().JWT_SECRET_KEY.encode(), value.encode("utf-8"), hashlib.sha256).hexdigest()

def _record_event(db: Session, order: Order, event_type: str, payload: dict) -> None:
    db.add(FulfillmentEvent(order_id=order.id, branch_id=order.branch_id, event_type=event_type, event_payload=payload))

def ensure_order_fulfillment(db: Session, order: Order) -> OrderFulfillment | None:
    if order.branch_id is None or order.fulfillment_method is None:
        return None
    row = db.scalar(select(OrderFulfillment).where(OrderFulfillment.order_id == order.id).with_for_update())
    if row is None:
        row = OrderFulfillment(order_id=order.id, branch_id=order.branch_id, method=order.fulfillment_method.value, status=FulfillmentStatus.AWAITING_PREPARATION)
        db.add(row); db.flush()
    return row

def mark_fulfillment_ready(db: Session, order: Order) -> OrderFulfillment:
    row = ensure_order_fulfillment(db, order)
    if row is None:
        raise ValueError("This order does not support branch fulfillment.")
    if row.status == FulfillmentStatus.AWAITING_PREPARATION:
        row.status = FulfillmentStatus.READY_FOR_COLLECTION
        row.ready_at = datetime.now(timezone.utc)
        db.add(row)
        _record_event(db, order, "fulfillment.ready_for_collection", {"order_id": order.id, "status": row.status})
    elif row.status != FulfillmentStatus.READY_FOR_COLLECTION:
        raise ValueError("Fulfillment is no longer awaiting collection.")
    return row

def issue_collection_credential(db: Session, order: Order, *, rotate: bool = False) -> dict:
    if order.branch_id is None or order.status != OrderStatus.PAID:
        raise ValueError("Only paid branch orders can receive collection credentials.")
    ticket = db.scalar(select(KitchenTicket).where(KitchenTicket.order_id == order.id).with_for_update())
    if ticket is None or ticket.status != KitchenTicketStatus.READY.value:
        raise ValueError("Collection credentials are available only after the kitchen marks the order ready.")
    fulfillment = ensure_order_fulfillment(db, order)
    if fulfillment is None or fulfillment.status != FulfillmentStatus.READY_FOR_COLLECTION:
        raise ValueError("This order is not ready for collection.")
    credential = db.scalar(select(CollectionCredential).where(CollectionCredential.order_id == order.id).with_for_update())
    now = datetime.now(timezone.utc)
    if credential is not None and not rotate:
        if credential.status == CollectionCredentialStatus.ISSUED:
            expiry = credential.expires_at if credential.expires_at.tzinfo else credential.expires_at.replace(tzinfo=timezone.utc)
            if expiry <= now:
                credential.status = CollectionCredentialStatus.EXPIRED
                db.add(credential); db.commit()
                raise ValueError("The collection credential has expired. Set rotate=true to issue a replacement.")
            raise ValueError("An active collection credential already exists. Set rotate=true only if it has been lost.")
        raise ValueError("A collection credential already exists. Set rotate=true to replace it.")
    token = secrets.token_urlsafe(32)
    pin = f"{secrets.randbelow(100_000_000):08d}"
    expires_at = now + timedelta(minutes=get_settings().COLLECTION_CREDENTIAL_TTL_MINUTES)
    if credential is None:
        credential = CollectionCredential(order_id=order.id, branch_id=order.branch_id, token_hash=_digest(token), pin_hash=_digest(pin), status=CollectionCredentialStatus.ISSUED, expires_at=expires_at)
        db.add(credential); event_type = "collection_credential.issued"
    else:
        credential.token_hash, credential.pin_hash = _digest(token), _digest(pin)
        credential.status, credential.expires_at, credential.issued_at = CollectionCredentialStatus.ISSUED, expires_at, now
        credential.redeemed_at = credential.redeemed_by_user_id = credential.redemption_method = None
        credential.handoff_name = credential.handoff_phone = None
        event_type = "collection_credential.rotated"
    _record_event(db, order, event_type, {"order_id": order.id, "expires_at": expires_at.isoformat()})
    db.commit(); db.refresh(credential)
    qr_payload = json.dumps({"type": "qless_collection", "token": token}, separators=(",", ":"), sort_keys=True)
    return {"order_id": order.id, "fulfillment_method": fulfillment.method, "qr_payload": qr_payload, "pin": pin, "expires_at": expires_at, "single_use": True}

def _extract_credential(raw: str, credential_type: str) -> str:
    if credential_type == "pin":
        if len(raw) != 8 or not raw.isdigit():
            raise ValueError("Collection PIN must contain exactly 8 digits.")
        return raw
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid collection QR payload.") from exc
    if not isinstance(payload, dict) or payload.get("type") != "qless_collection":
        raise ValueError("Unsupported collection QR payload.")
    token = payload.get("token")
    if not isinstance(token, str) or not 32 <= len(token) <= 128:
        raise ValueError("Invalid collection QR token.")
    return token

def redeem_collection_credential(db: Session, *, branch_id, raw_credential: str, credential_type: str, staff_user_id, handoff_name: str | None = None, handoff_phone: str | None = None) -> dict:
    raw = _extract_credential(raw_credential, credential_type)
    digest = _digest(raw)
    column = CollectionCredential.pin_hash if credential_type == "pin" else CollectionCredential.token_hash
    credential = db.scalar(select(CollectionCredential).where(column == digest, CollectionCredential.branch_id == branch_id).with_for_update())
    if credential is None:
        raise ValueError("Collection credential is invalid for this branch.")
    now = datetime.now(timezone.utc)
    expires = credential.expires_at if credential.expires_at.tzinfo else credential.expires_at.replace(tzinfo=timezone.utc)
    if credential.status != CollectionCredentialStatus.ISSUED:
        raise ValueError("Collection credential has already been used or revoked.")
    if expires <= now:
        credential.status = CollectionCredentialStatus.EXPIRED
        db.add(credential); db.commit()
        raise ValueError("Collection credential has expired.")
    order = db.get(Order, credential.order_id)
    if order is None or order.status != OrderStatus.PAID:
        raise ValueError("Order is not eligible for handoff.")
    fulfillment = db.scalar(select(OrderFulfillment).where(OrderFulfillment.order_id == order.id).with_for_update())
    if fulfillment is None or fulfillment.status != FulfillmentStatus.READY_FOR_COLLECTION:
        raise ValueError("Order is not ready for collection.")
    if order.fulfillment_method == FulfillmentMethod.EXTERNAL_RIDER and (not handoff_name or not handoff_phone):
        raise ValueError("Rider name and phone number are required to record an external-rider handoff.")
    credential.status, credential.redeemed_at = CollectionCredentialStatus.REDEEMED, now
    credential.redeemed_by_user_id, credential.redemption_method = staff_user_id, credential_type
    credential.handoff_name, credential.handoff_phone = handoff_name, handoff_phone
    fulfillment.status = FulfillmentStatus.RIDER_COLLECTED if order.fulfillment_method == FulfillmentMethod.EXTERNAL_RIDER else FulfillmentStatus.COLLECTED
    fulfillment.completed_at = now
    db.add_all([credential, fulfillment])
    event_type = "fulfillment.rider_collected" if fulfillment.status == FulfillmentStatus.RIDER_COLLECTED else "fulfillment.collected"
    _record_event(db, order, event_type, {"order_id": order.id, "status": fulfillment.status, "redeemed_by_user_id": str(staff_user_id), "redemption_method": credential_type, "handoff_name": handoff_name, "handoff_phone": handoff_phone})
    db.commit()
    return {"order_id": order.id, "fulfillment_status": fulfillment.status, "fulfillment_method": fulfillment.method, "redeemed_at": now}

def get_order_fulfillment(db: Session, order_id: int) -> OrderFulfillment | None:
    return db.scalar(select(OrderFulfillment).where(OrderFulfillment.order_id == order_id))
