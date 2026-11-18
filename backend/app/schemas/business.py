"""Business, branch and membership API schemas."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.business import BusinessType
from app.models.business_membership import BusinessRole

class BusinessCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    business_type: BusinessType = BusinessType.INDEPENDENT
    description: Optional[str] = Field(default=None, max_length=5000)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=40)

class BusinessUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=40)
    is_active: Optional[bool] = None
    model_config = ConfigDict(extra="forbid")

class BusinessResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    business_type: BusinessType
    description: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BusinessWithRoleResponse(BusinessResponse):
    membership_role: Optional[BusinessRole] = None

class BranchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    address_line: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    country: str = Field(default="NG", min_length=2, max_length=2)
    phone: Optional[str] = Field(default=None, max_length=40)
    timezone: str = Field(default="Africa/Lagos", min_length=1, max_length=64)
    notes: Optional[str] = Field(default=None, max_length=5000)

class BranchUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    address_line: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    phone: Optional[str] = Field(default=None, max_length=40)
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    notes: Optional[str] = Field(default=None, max_length=5000)
    is_active: Optional[bool] = None
    model_config = ConfigDict(extra="forbid")

class BranchResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    slug: str
    address_line: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: str
    phone: Optional[str]
    timezone: str
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MembershipCreate(BaseModel):
    user_id: uuid.UUID
    role: BusinessRole
    branch_id: Optional[uuid.UUID] = None

class MembershipUpdate(BaseModel):
    is_active: bool

class MembershipResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID]
    role: BusinessRole
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BranchQRResponse(BaseModel):
    branch_id: uuid.UUID
    token: uuid.UUID
    menu_url: str

class PublicBranchResolveResponse(BaseModel):
    business_id: uuid.UUID
    business_name: str
    branch_id: uuid.UUID
    branch_name: str
    address_line: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: str
    timezone: str
