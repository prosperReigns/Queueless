"""Notification token service logic."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification_token import NotificationToken


def upsert_notification_token(
    db: Session,
    *,
    user_id: uuid.UUID,
    token: str,
    device_type: str | None = None,
) -> NotificationToken:
    """Create or reassign a notification token to the authenticated user."""
    normalized_token = token.strip()
    normalized_device_type = device_type.strip() if isinstance(device_type, str) else None
    if normalized_device_type == "":
        normalized_device_type = None

    existing_token = db.scalar(
        select(NotificationToken).where(NotificationToken.token == normalized_token)
    )
    if existing_token is not None:
        existing_token.user_id = user_id
        existing_token.device_type = normalized_device_type
        db.add(existing_token)
        db.commit()
        db.refresh(existing_token)
        return existing_token

    if normalized_device_type:
        existing_device_token = db.scalar(
            select(NotificationToken).where(
                NotificationToken.user_id == user_id,
                NotificationToken.device_type == normalized_device_type,
            )
        )
        if existing_device_token is not None:
            existing_device_token.token = normalized_token
            db.add(existing_device_token)
            db.commit()
            db.refresh(existing_device_token)
            return existing_device_token

    new_token = NotificationToken(
        user_id=user_id,
        token=normalized_token,
        device_type=normalized_device_type,
    )
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    return new_token


def list_user_notification_tokens(db: Session, user_id: uuid.UUID) -> list[NotificationToken]:
    """Return all active notification tokens for a user."""
    stmt = (
        select(NotificationToken)
        .where(NotificationToken.user_id == user_id)
        .order_by(NotificationToken.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def delete_notification_token_by_value(db: Session, token: str) -> bool:
    """Delete a token record and return True when a row was removed."""
    existing_token = db.scalar(select(NotificationToken).where(NotificationToken.token == token))
    if existing_token is None:
        return False
    db.delete(existing_token)
    db.commit()
    return True


def delete_notification_tokens_by_values(db: Session, tokens: list[str]) -> int:
    """Delete token records for the given token values and return deleted count."""
    if not tokens:
        return 0
    stmt = select(NotificationToken).where(NotificationToken.token.in_(tokens))
    records = list(db.scalars(stmt).all())
    for record in records:
        db.delete(record)
    db.commit()
    return len(records)
