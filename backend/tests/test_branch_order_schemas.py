"""Schema-level tests for the branch-aware checkout contract."""
import uuid
import pytest
from pydantic import ValidationError
from app.schemas.branch_order import BranchOrderCreate, OrderSource, FulfillmentMethod

def payload(**overrides):
    data = {
        "branch_id": str(uuid.uuid4()),
        "source": "preorder",
        "fulfillment_method": "self_collection",
        "customer_name": "Test Customer",
        "customer_email": "customer@example.com",
        "customer_phone": "+2348012345678",
        "items": [{"menu_item_id": str(uuid.uuid4()), "quantity": 2}],
    }
    data.update(overrides)
    return data

def test_remote_preorder_uses_selected_branch_without_qr_token():
    request = BranchOrderCreate.model_validate(payload())
    assert request.source == OrderSource.PREORDER
    assert request.branch_id is not None
    assert request.branch_qr_token is None

def test_onsite_order_accepts_permanent_branch_qr_identity():
    token = uuid.uuid4()
    request = BranchOrderCreate.model_validate(payload(
        branch_id=None, branch_qr_token=str(token), source="onsite_qr",
        fulfillment_method="external_rider",
    ))
    assert request.branch_qr_token == token
    assert request.fulfillment_method == FulfillmentMethod.EXTERNAL_RIDER

def test_checkout_rejects_non_positive_or_excessive_quantity():
    with pytest.raises(ValidationError):
        BranchOrderCreate.model_validate(payload(items=[{
            "menu_item_id": str(uuid.uuid4()), "quantity": 0
        }]))
    with pytest.raises(ValidationError):
        BranchOrderCreate.model_validate(payload(items=[{
            "menu_item_id": str(uuid.uuid4()), "quantity": 51
        }]))
