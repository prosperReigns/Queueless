"""Collection credential parsing and fulfillment status tests."""
import json
import pytest

from app.models.fulfillment import FulfillmentStatus
from app.services.fulfillment_service import _extract_credential


def test_qr_collection_payload_extracts_secret_token():
    token = "a" * 43
    payload = json.dumps({"type": "qless_collection", "token": token})
    assert _extract_credential(payload, "qr") == token


def test_pin_must_be_exactly_eight_digits():
    assert _extract_credential("00123456", "pin") == "00123456"
    for invalid in ("1234567", "123456789", "1234abcd"):
        with pytest.raises(ValueError):
            _extract_credential(invalid, "pin")


def test_branch_qr_is_not_a_collection_qr():
    with pytest.raises(ValueError):
        _extract_credential('{"type":"branch_menu","token":"x"}', "qr")


def test_customer_pickup_and_rider_handoff_are_distinct():
    assert FulfillmentStatus.COLLECTED != FulfillmentStatus.RIDER_COLLECTED
