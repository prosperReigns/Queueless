"""Notification endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.core.config import get_settings
from app.core.rate_limiter import limiter
from app.models.user import User
from app.schemas.notification import (
    NotificationTokenResponse,
    NotificationTokenUpsertRequest,
    NotificationTokenUpsertResponse,
)
from app.services.notification_token_service import upsert_notification_token

router = APIRouter(prefix="/notifications", tags=["notifications"])
settings = get_settings()


@router.post("/token", response_model=NotificationTokenUpsertResponse, status_code=status.HTTP_200_OK)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def upsert_notification_token_endpoint(
    request: Request,
    payload: NotificationTokenUpsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> NotificationTokenUpsertResponse:
    """Register or update an FCM token for the authenticated user."""
    token_record = upsert_notification_token(
        db,
        user_id=current_user.id,
        token=payload.fcm_token,
        device_type=payload.device_type,
    )

    return NotificationTokenUpsertResponse(
        message="Notification token saved successfully.",
        token=NotificationTokenResponse(
            id=token_record.id,
            user_id=str(token_record.user_id),
            token=token_record.token,
            device_type=token_record.device_type,
        ),
    )
