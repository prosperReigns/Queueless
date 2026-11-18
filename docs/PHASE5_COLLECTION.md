# Phase 5 — Collection and external rider handoff

Phase 5 implements the final physical handoff step for paid branch orders. It does not build a Qless rider fleet or track a customer-arranged rider after the rider leaves the branch.

## Fulfillment lifecycle

Payment/order state, kitchen state and physical fulfillment state are separate:

- Payment verification marks the order `PAID`.
- Kitchen tickets move through `NEW → ACCEPTED → PREPARING → READY`.
- Fulfillment starts as `awaiting_preparation`, then becomes `ready_for_collection` when the kitchen ticket reaches `READY`.
- Successful single-use handoff changes fulfillment to `collected` for self-collection or `rider_collected` for a customer-arranged external rider.
- The order's payment/order status is not rewritten to represent a physical handoff.

## Collection credentials

A customer/guest may issue a credential only after the kitchen marks their paid order ready. The API returns:
- A QR payload containing a cryptographically random token.
- An eight-digit numeric PIN as an alternative for manual entry.
- An expiry timestamp (default 180 minutes; configurable from 15 to 1440 minutes).

Only SHA-256 hashes are stored. The QR/PIN are displayed in the issuance response and cannot be retrieved from the database afterward. If lost or expired, the owner can explicitly rotate the credential; rotation invalidates the previous token and PIN. Issuance is rate-limited.

The permanent branch QR is never accepted by the collection redemption endpoint.

## API

- `GET /api/v1/orders/{order_id}/tracking` — customer or guest-token tracking.
- `POST /api/v1/orders/{order_id}/collection-credential` — issue a QR/PIN; send guest orders' token in `X-Guest-Access-Token`. Set `{"rotate": true}` only to replace a lost/expired credential.
- `POST /api/v1/branches/{branch_id}/collection/redeem` — collection staff scan the QR payload or enter the PIN. Request body includes `credential_type` (`qr` or `pin`), `credential`, and optional rider name/phone for the handoff record.

Collection redemption is branch-scoped to owner, franchise-admin, branch-manager and collection-staff memberships (plus platform admins). Kitchen staff and cashiers are not granted collection privileges by default.

## Atomicity and audit

Redemption locks the credential and fulfillment rows, verifies the issuing branch, expiry, unused state, paid order and ready fulfillment, then marks the credential redeemed and records the handoff event in one transaction. Replays and simultaneous attempts cannot reuse a redeemed credential. Events contain no QR token or PIN.

## Migration and verification

Alembic revision: `e6f2a9c4d810` (parent `d4b8e1a6c903`). Existing branch orders are backfilled into fulfillment records; legacy store orders remain unchanged.

Run from `backend/`:

```bash
python -m compileall app tests
pytest -q
alembic upgrade head
```

Test a fresh database and a disposable copy of the existing PostgreSQL database. Before production, exercise both QR and PIN redemption, wrong-branch attempts, expired and rotated credentials, duplicate/concurrent redemption, guest and logged-in customer authorization, and both self-collection and external-rider handoff.
