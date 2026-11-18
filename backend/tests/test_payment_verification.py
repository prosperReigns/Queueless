"""Focused tests for payment verification invariants."""
from decimal import Decimal
import pytest

from app.models.payment import Payment, PaymentProvider, PaymentStatus
from app.services.payment_service import _validate_verified_transaction, verify_paystack_webhook_signature


def _payment():
    return Payment(
        order_id=1,
        reference="qls-test-reference",
        status=PaymentStatus.PENDING,
        amount=Decimal("1250.00"),
        currency="NGN",
        provider=PaymentProvider.PAYSTACK,
    )


def _verified_data(**overrides):
    data = {
        "reference": "qls-test-reference",
        "status": "success",
        "amount": 125000,
        "currency": "NGN",
        "id": 123456789,
    }
    data.update(overrides)
    return data


def test_verified_transaction_accepts_exact_reference_amount_and_currency():
    _validate_verified_transaction(_payment(), _verified_data())


@pytest.mark.parametrize(
    "overrides",
    [
        {"reference": "some-other-payment"},
        {"amount": 124999},
        {"currency": "USD"},
    ],
)
def test_verified_transaction_rejects_reference_amount_or_currency_mismatch(overrides):
    with pytest.raises(ValueError):
        _validate_verified_transaction(_payment(), _verified_data(**overrides))


def test_webhook_signature_uses_constant_time_hmac_validation():
    import hashlib
    import hmac

    raw_body = b'{"event":"charge.success","data":{"reference":"qls-test-reference"}}'
    signature = hmac.new(b"test_paystack_secret", raw_body, hashlib.sha512).hexdigest()
    assert verify_paystack_webhook_signature(raw_body, signature) is True
    assert verify_paystack_webhook_signature(raw_body, "bad-signature") is False
