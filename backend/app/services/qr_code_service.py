"""QR code generation and validation service."""

from __future__ import annotations

import base64
import io
import json
from typing import Any

import qrcode
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus


def _build_qr_payload(order: Order) -> dict[str, Any]:
    """Build canonical QR payload for an order."""
    return {"type": "order_pickup", "order_id": order.id}


def get_order_qr_data(order: Order) -> str:
    """Return serialized QR content for an order."""
    return json.dumps(_build_qr_payload(order), separators=(",", ":"), sort_keys=True)


def generate_order_qr_image_base64(order: Order) -> str:
    """Generate PNG QR image bytes and return base64 representation."""
    qr_data = get_order_qr_data(order)
    image = qrcode.make(qr_data)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _parse_qr_data(qr_data: str) -> tuple[int | None, str | None]:
    """Extract order id from QR data payload."""
    try:
        payload = json.loads(qr_data)
    except json.JSONDecodeError:
        return None, "Invalid QR payload format."

    if not isinstance(payload, dict):
        return None, "Invalid QR payload format."

    if payload.get("type") != "order_pickup":
        return None, "Unsupported QR payload type."

    order_id = payload.get("order_id")
    if not isinstance(order_id, int) or order_id <= 0:
        return None, "Invalid order reference in QR payload."
    return order_id, None


def validate_scanned_qr_data(db: Session, qr_data: str) -> tuple[bool, str, Order | None]:
    """Validate scanned order QR content and resolve referenced order."""
    order_id, parse_error = _parse_qr_data(qr_data)
    if parse_error:
        return False, parse_error, None

    order = db.get(Order, order_id)
    if order is None:
        return False, "Order not found.", None

    return True, "QR code is valid.", order


def is_order_pickup_ready(order: Order) -> bool:
    """Return whether the order is currently valid for pickup."""
    return order.status in {OrderStatus.READY, OrderStatus.COMPLETED}
