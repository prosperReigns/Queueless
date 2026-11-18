"""Request/response schemas for collection and handoff."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CollectionCredentialIssueRequest(BaseModel):
    rotate: bool = False


class CollectionCredentialResponse(BaseModel):
    order_id: int
    fulfillment_method: str
    qr_payload: str
    pin: str
    expires_at: datetime
    single_use: bool = True


class CollectionRedemptionRequest(BaseModel):
    credential_type: Literal["qr", "pin"]
    credential: str = Field(min_length=1, max_length=512)
    handoff_name: Optional[str] = Field(default=None, max_length=160)
    handoff_phone: Optional[str] = Field(default=None, min_length=7, max_length=40)


class FulfillmentTrackingResponse(BaseModel):
    order_id: int
    order_status: str
    kitchen_status: Optional[str] = None
    fulfillment_method: Optional[str] = None
    fulfillment_status: Optional[str] = None
    branch_id: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    updated_at: Optional[datetime] = None
