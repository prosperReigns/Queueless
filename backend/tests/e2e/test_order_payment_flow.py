"""End-to-end API flow test for order + payment lifecycle."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Dict


def _auth_headers(access_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _register(client, *, email: str, password: str, role: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login(client, *, email: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["refresh_token"]
    return payload


def test_e2e_customer_order_payment_and_merchant_completion_flow(client):
    """Simulate register/login/create/order/pay/webhook/status-complete end-to-end flow."""

    # 1) User registers (customer + merchant needed for full flow).
    customer = _register(
        client,
        email="customer@example.com",
        password="StrongPass123",
        role="customer",
    )
    merchant = _register(
        client,
        email="merchant@example.com",
        password="StrongPass123",
        role="merchant",
    )
    assert customer["role"] == "customer"
    assert merchant["role"] == "merchant"

    # 2) User logs in.
    customer_tokens = _login(client, email="customer@example.com", password="StrongPass123")
    merchant_tokens = _login(client, email="merchant@example.com", password="StrongPass123")

    # 3) Merchant creates store + product.
    create_store_resp = client.post(
        "/api/v1/stores",
        json={
            "name": "Merchant Store",
            "description": "A sample merchant store",
            "location": "Lagos",
            "is_active": True,
        },
        headers=_auth_headers(merchant_tokens["access_token"]),
    )
    assert create_store_resp.status_code == 201, create_store_resp.text
    store = create_store_resp.json()
    assert store["name"] == "Merchant Store"
    assert store["owner_id"] == merchant["id"]

    create_product_resp = client.post(
        "/api/v1/products",
        json={
            "store_id": store["id"],
            "name": "Test Product",
            "description": "Fresh product",
            "price": "1500.00",
            "is_available": True,
            "image_url": "https://example.com/product.jpg",
        },
        headers=_auth_headers(merchant_tokens["access_token"]),
    )
    assert create_product_resp.status_code == 201, create_product_resp.text
    product = create_product_resp.json()
    assert product["store_id"] == store["id"]
    assert product["price"] == "1500.00"

    # 4) Customer places order.
    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "store_id": store["id"],
            "items": [{"product_id": product["id"], "quantity": 2}],
        },
        headers=_auth_headers(customer_tokens["access_token"]),
    )
    assert create_order_resp.status_code == 201, create_order_resp.text
    order = create_order_resp.json()
    assert order["status"] == "pending"
    assert order["store_id"] == store["id"]
    assert order["user_id"] == customer["id"]
    assert order["total_amount"] == "3000.00"
    assert len(order["items"]) == 1
    assert order["items"][0]["product_id"] == product["id"]
    assert order["items"][0]["quantity"] == 2

    # 5) Customer initiates payment (mocked provider call).
    initiate_payment_resp = client.post(
        "/api/v1/payments/initiate",
        json={"order_id": order["id"], "callback_url": "https://example.com/callback"},
        headers=_auth_headers(customer_tokens["access_token"]),
    )
    assert initiate_payment_resp.status_code == 200, initiate_payment_resp.text
    payment_init = initiate_payment_resp.json()
    assert payment_init["authorization_url"] == "https://paystack.test/authorize"
    assert payment_init["access_code"] == "test_access_code"
    assert payment_init["reference"] == order["payment_reference"]
    assert payment_init["payment"]["order_id"] == order["id"]
    assert payment_init["payment"]["status"] == "pending"
    assert payment_init["payment"]["amount"] == "3000.00"

    # 6) Webhook updates order.
    webhook_payload = {
        "event": "charge.success",
        "data": {
            "reference": order["payment_reference"],
        },
    }
    raw_body = json.dumps(webhook_payload).encode("utf-8")
    secret = "test_paystack_secret"
    signature = hmac.new(secret.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha512).hexdigest()

    webhook_resp = client.post(
        "/api/v1/payments/webhook",
        content=raw_body,
        headers={"x-paystack-signature": signature, "content-type": "application/json"},
    )
    assert webhook_resp.status_code == 200, webhook_resp.text
    webhook_data = webhook_resp.json()
    assert webhook_data["status"] == "ok"
    assert webhook_data["processed"] == "true"
    assert webhook_data["reason"] == "verified_success"

    duplicate_webhook_resp = client.post(
        "/api/v1/payments/webhook",
        content=raw_body,
        headers={"x-paystack-signature": signature, "content-type": "application/json"},
    )
    assert duplicate_webhook_resp.status_code == 200
    assert duplicate_webhook_resp.json()["reason"] == "duplicate_event"

    verify_response = client.post(
        "/api/v1/payments/verify",
        json={"reference": order["payment_reference"]},
        headers=_auth_headers(customer_tokens["access_token"]),
    )
    assert verify_response.status_code == 200, verify_response.text
    assert verify_response.json()["provider_status"] == "success"
    assert verify_response.json()["payment"]["status"] == "success"
    assert verify_response.json()["order_status"] == "paid"

    customer_order_after_webhook = client.get(
        f"/api/v1/orders/{order['id']}",
        headers=_auth_headers(customer_tokens["access_token"]),
    )
    assert customer_order_after_webhook.status_code == 200, customer_order_after_webhook.text
    assert customer_order_after_webhook.json()["status"] == "paid"

    # 7) Merchant updates order status.
    preparing_resp = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "preparing"},
        headers=_auth_headers(merchant_tokens["access_token"]),
    )
    assert preparing_resp.status_code == 200, preparing_resp.text
    assert preparing_resp.json()["status"] == "preparing"

    ready_resp = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "ready"},
        headers=_auth_headers(merchant_tokens["access_token"]),
    )
    assert ready_resp.status_code == 200, ready_resp.text
    assert ready_resp.json()["status"] == "ready"

    # 8) Order is completed.
    completed_resp = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "completed"},
        headers=_auth_headers(merchant_tokens["access_token"]),
    )
    assert completed_resp.status_code == 200, completed_resp.text
    assert completed_resp.json()["status"] == "completed"

    # 9) Merchant initiates a partial refund with an idempotency key.
    refund_payload = {
        "idempotency_key": "refund-e2e-0001",
        "payment_reference": order["payment_reference"],
        "amount": "500.00",
        "reason": "Partial customer refund",
    }
    refund_resp = client.post(
        "/api/v1/payments/refunds",
        json=refund_payload,
        headers=_auth_headers(merchant_tokens["access_token"]),
    )
    assert refund_resp.status_code == 201, refund_resp.text
    refund = refund_resp.json()
    assert refund["status"] == "pending"
    assert refund["amount"] == "500.00"

    # A client retry with the same key returns the same refund; it does not call Paystack again.
    refund_retry_resp = client.post(
        "/api/v1/payments/refunds",
        json=refund_payload,
        headers=_auth_headers(merchant_tokens["access_token"]),
    )
    assert refund_retry_resp.status_code == 201, refund_retry_resp.text
    assert refund_retry_resp.json()["id"] == refund["id"]
    assert refund_retry_resp.json()["reference"] == refund["reference"]

    refund_reconcile_resp = client.post(
        f"/api/v1/payments/refunds/{refund['reference']}/reconcile",
        headers=_auth_headers(merchant_tokens["access_token"]),
    )
    assert refund_reconcile_resp.status_code == 200, refund_reconcile_resp.text
    assert refund_reconcile_resp.json()["status"] == "processed"

    # A late refund webhook is also idempotent and does not double-count the refunded amount.
    refund_webhook_payload = {
        "event": "refund.processed",
        "data": {
            "id": 123456,
            "refund_reference": refund["reference"],
            "transaction_reference": order["payment_reference"],
            "amount": 50000,
            "currency": "NGN",
        },
    }
    refund_raw_body = json.dumps(refund_webhook_payload).encode("utf-8")
    refund_signature = hmac.new(secret.encode("utf-8"), msg=refund_raw_body, digestmod=hashlib.sha512).hexdigest()
    refund_webhook_resp = client.post(
        "/api/v1/payments/webhook",
        content=refund_raw_body,
        headers={"x-paystack-signature": refund_signature, "content-type": "application/json"},
    )
    assert refund_webhook_resp.status_code == 200, refund_webhook_resp.text
    assert refund_webhook_resp.json()["reason"] == "refund_processed"

    refund_duplicate_resp = client.post(
        "/api/v1/payments/webhook",
        content=refund_raw_body,
        headers={"x-paystack-signature": refund_signature, "content-type": "application/json"},
    )
    assert refund_duplicate_resp.status_code == 200
    assert refund_duplicate_resp.json()["reason"] == "duplicate_event"

    verified_after_refund = client.post(
        "/api/v1/payments/verify",
        json={"reference": order["payment_reference"]},
        headers=_auth_headers(customer_tokens["access_token"]),
    )
    assert verified_after_refund.status_code == 200
    assert verified_after_refund.json()["payment"]["status"] == "success"
    assert verified_after_refund.json()["payment"]["amount_refunded"] == "500.00"
    assert verified_after_refund.json()["order_status"] == "completed"

    final_customer_view = client.get(
        f"/api/v1/orders/{order['id']}",
        headers=_auth_headers(customer_tokens["access_token"]),
    )
    assert final_customer_view.status_code == 200, final_customer_view.text
    assert final_customer_view.json()["status"] == "completed"
