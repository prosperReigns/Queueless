# Phase 3 — Payment correctness

All routes are under `/api/v1`. Paystack remains the provider in this phase.

## Payment and order state are separate

A `Payment` represents the money movement; an `Order` represents fulfillment. A successful payment is verified and recorded before the order transitions from `pending` to `paid`. Kitchen/fulfillment transitions remain order lifecycle operations. A failed payment does not automatically cancel the order; the existing unpaid-order expiry policy remains responsible for expiry.

Payment status values remain `pending`, `success`, and `failed`. Refunds have their own records and statuses; a partially or fully refunded payment remains a successful original charge with an auditable refund balance.

## Payment endpoints

### Initialize

`POST /payments/initiate`

Authenticated customers can initialize their own order. Guest checkout can initialize using its 24-hour guest token. Repeated initialization returns the stored authorization URL/access code when available instead of creating a second local payment record.

### Verify after checkout

`POST /payments/verify`

```json
{
  "reference": "ORDER_PAYMENT_REFERENCE",
  "guest_access_token": "only-for-guest-orders"
}
```

The backend calls Paystack's transaction verify endpoint. It compares the provider's reference, status, amount in minor units, and currency with the stored payment. The browser's success callback is never treated as proof of payment. Only verified success updates the payment and, where the order is still pending, moves the order to paid.

### Webhook

`POST /payments/webhook`

Paystack's `x-paystack-signature` is checked using HMAC-SHA512 over the raw request body. For `charge.success`, Qless independently verifies the transaction with Paystack before applying payment state. The webhook event is recorded using a canonical payload SHA-256 fingerprint and a unique provider/event key. Duplicate deliveries are acknowledged without repeating state transitions. A transient verification outage returns HTTP 503 so Paystack can retry; a verified mismatch is recorded and not fulfilled.

Refund pending, processing, needs-attention, failed and processed events update the matching refund record. Qless matches Paystack's refund reference/provider ID where present, and falls back to transaction reference plus amount only when exactly one pending local refund matches. Refund completion increases the recorded refunded amount once.

### Refund

`POST /payments/refunds`

```json
{
  "idempotency_key": "refund-request-2026-0001",
  "payment_reference": "ORDER_PAYMENT_REFERENCE",
  "amount": "500.00",
  "reason": "Customer requested refund"
}
```

Omit `amount` to refund the remaining refundable balance. Only successful payments can be refunded. Access is limited to Qless admins, authorized business owners/franchise admins/branch managers, or the legacy store owner. Refund amounts are reserved against pending refund requests to prevent concurrent over-refunding. Every request must include a stable client-generated idempotency key; retrying the same request returns the existing refund record instead of issuing another refund.

Paystack refund requests use a unique Qless-generated refund reference. Provider outcomes are stored as `pending`, `processing`, `processed`, `failed`, `needs_attention`, or `pending_unknown`. If the request times out, do not blindly submit another refund: use reconciliation first.

### Reconcile uncertain refund

`POST /payments/refunds/{refund_reference}/reconcile`

Fetches the refund from Paystack by the Qless refund reference and updates its state. The same merchant/admin authorization rules apply.

## Audit tables

- `payment_events`: webhook fingerprint, event type, reference, processing outcome and timestamps.
- `payment_status_history`: previous/new status, source (initialization, webhook, manual verification or fallback), note and timestamp.
- `payment_refunds`: unique Qless refund reference, amount, provider refund ID, status, initiator and timestamps.

The `payments` table now also stores currency, provider transaction ID, checkout authorization metadata, paid timestamp, failure reason, refunded amount and updated timestamp.

## Reconciliation behavior

The customer verification endpoint and delayed Celery fallback both use the same Paystack verification and validation path. They require the provider's reference, currency and amount to match the stored payment before applying success. The fallback is not allowed to mark an order paid based on a webhook payload or a client callback.

## Configuration

- `PAYSTACK_SECRET_KEY`: server-only Paystack secret.
- `PAYSTACK_BASE_URL`: defaults to `https://api.paystack.co`.
- `PAYMENT_CURRENCY`: three-letter ISO currency, defaults to `NGN`.

Never expose the Paystack secret key to the frontend. Set webhook URL to `/api/v1/payments/webhook` in the Paystack dashboard.

## Migration

Alembic revision `c7a4d91e2f60` follows Phase 2 revision `b2e6c19a7d41`. It adds payment metadata and the three audit/refund tables without rewriting legacy order/payment rows. Existing payments receive `NGN` and a zero refunded amount as migration defaults.

## Verification still required

Run the backend tests and migration checks before merging:

```bash
cd backend
pytest -q
python -m compileall app tests
alembic upgrade head
```

Apply migrations first to a fresh PostgreSQL database and then to a disposable backup of an existing database. Test Paystack test-mode initialization, verify, duplicate webhook, amount/currency mismatch, delayed fallback, partial refund, full refund, refund timeout and refund reconciliation. No live Paystack transaction or production database migration has been executed by this implementation.
