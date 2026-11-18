# Qless SRS Alignment and Migration Plan

## Purpose

This document maps the existing Queueless implementation to the agreed Qless SRS and defines a safe, incremental migration. The existing application is a useful working foundation; this plan deliberately avoids a destructive rewrite.

## Repository baseline reviewed

- Backend: FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, JWT, Redis/Celery, Paystack, WebSockets, Firebase notifications.
- Frontend: React 19, TypeScript, Vite, React Router, TanStack Query, Axios, Firebase Cloud Messaging.
- Existing domains: users, stores, products, orders, order items, payments, notification tokens, order QR codes.
- Existing tests and payment/order service logic are present.

## Main gaps against the Qless SRS

1. The data model is centred on a single `Store` owned directly by one merchant. Qless needs `Business → Branch`, supporting independent restaurants and multi-branch franchises.
2. Authorization is based on one global user role (`CUSTOMER`, `MERCHANT`, `ADMIN`). Qless requires business/branch memberships and scoped roles such as owner, franchise admin, branch manager, cashier, kitchen staff and collection staff.
3. Orders point to a store, but do not explicitly capture the branch, source channel (`preorder` or `onsite_qr`), fulfillment method, scheduled slot, guest customer details or branch-specific context.
4. Payment and order states are coupled: successful payment currently advances the order to `PAID`. The target keeps payment state and operational order state separate.
5. The current QR implementation is an order QR containing a predictable order ID. Qless needs a permanent branch QR for menu entry and a separate short-lived, single-use order collection credential.
6. The current workflow has merchant order status updates but no dedicated kitchen display workflow or fulfillment handoff workflow.
7. Product availability/pricing is store-scoped; the target needs centrally managed business menu items with branch-level availability and optional branch-specific pricing.
8. The current model needs explicit order status history, payment event/idempotency records, refunds, fulfillment/collection events, audit logs and durable notification/outbox handling.
9. The initial Alembic migration currently contains no schema operations. Before production rollout, the actual database schema and migration history must be reconciled and a real baseline/forward migration strategy established.

## Target domain model

- Identity: users, customer profiles, business memberships, role assignments.
- Business: businesses, branches, branch operating hours, branch QR tokens.
- Menu: menus, categories, menu items, option groups/values, branch item overrides.
- Commerce: carts, cart items, orders, immutable order item snapshots.
- Payments: payments, payment events, refunds, reconciliation records.
- Kitchen: kitchen stations, kitchen order tickets, kitchen item progress.
- Fulfillment: fulfillments, delivery assignments, collection credentials, collection events.
- Platform: notifications, notification outbox, audit logs, status histories.

## Compatibility and migration rules

- Keep existing API paths and legacy `stores` behaviour available during the transition.
- Introduce the new business/branch domain additively, with explicit legacy mapping. Do not silently reinterpret a store as a branch until the data migration and API compatibility layer are tested.
- Use Alembic migrations; never rely on application startup `create_all` as the production schema migration strategy.
- Keep existing order and payment records readable. Backfill business/branch references only after each legacy store has a deterministic business and branch mapping.
- Do not delete legacy tables or columns in the first migration phases.
- Use decimal-safe or integer-minor-unit money values; never floating-point arithmetic.
- Enforce tenant and branch scope in backend queries and dependencies, not only in frontend route guards.

## Delivery sequence

### Phase 0 — Baseline and safety
- Confirm current default branch, dependencies, tests, deployment settings and real database schema.
- Ensure generated environments/virtualenvs and secrets are not committed.
- Establish a working Alembic baseline without destroying existing data.
- Run existing backend tests and frontend lint/build before changing domain behaviour.

### Phase 1 — Business, branch and membership foundation
- Add businesses, branches, memberships and scoped role assignments.
- Add branch operating hours and branch QR token records.
- Add owner/franchise-admin/branch-manager access rules.
- Keep legacy merchant/store APIs operating through a compatibility layer.

### Phase 2 — Branch-aware menu and ordering
- Add menu categories/items and branch availability/pricing overrides.
- Add source channel, branch, fulfillment method, scheduled pickup, guest checkout and immutable item snapshots to orders.
- Make remote preorder and onsite QR use the same order creation service.

### Phase 3 — Payment correctness
- Separate payment status from order status.
- Verify provider amount, currency, reference and successful status server-side.
- Persist webhook event IDs/payload hashes and process idempotently.
- Add refund and reconciliation workflows.
- Keep Paystack behind a provider interface so another provider can be added without rewriting order logic.

### Phase 4 — Kitchen operations and realtime
- Add kitchen tickets and explicit NEW → ACCEPTED → PREPARING → READY transitions.
- Scope kitchen queues to a branch.
- Publish durable events; use WebSockets as a delivery mechanism, not as the source of truth.
- Preserve polling fallback.

### Phase 5 — Collection and external rider handoff
- Add self-pickup and customer-arranged external rider fulfillment.
- Generate high-entropy, hashed, branch-bound, expiring, single-use collection credentials.
- Validate readiness, payment and branch before atomic redemption.
- Track COLLECTED / RIDER_COLLECTED / OUT_FOR_DELIVERY / DELIVERED separately.
- Do not build a Qless-managed rider fleet in the MVP.

### Phase 6 — Role-based frontends and reporting
- Customer: discovery, branch selection, preorder, QR menu, checkout, tracking and order history.
- Merchant: business/franchise/branch setup, staff, menu and branch operations.
- Kitchen: focused KDS queue.
- Fulfillment: secure QR/PIN validation and handoff.
- Reports: waiting, preparation, payment and collection metrics.

## Acceptance gates

- Both order channels create orders through the same service and persist their origin.
- A branch manager cannot read or mutate another branch's data.
- A franchise administrator can access only assigned businesses/branches.
- A successful payment is independently verified and cannot be duplicated by repeated webhooks.
- A paid order appears in the correct branch kitchen queue.
- A collection credential cannot be reused, guessed, used at another branch, or redeemed before the order is ready.
- Notification failure does not roll back or lose an accepted order.
- Existing customers, stores, products and orders remain accessible during migration.


## Phase 1 implementation status

Implemented on `feature/qless-srs-alignment`:

- Added tenant models for businesses, branches, memberships and permanent branch QR identities.
- Added business and branch API schemas, services and authenticated endpoints.
- Business creator receives the owner membership automatically.
- Added branch-level staff roles and business-level owner/franchise-admin roles with database scope constraints.
- Added server-side business/branch access checks; branch staff only receive their assigned branch list.
- Added permanent branch QR resolution endpoint. It does not authorize order collection.
- Added migration revision `91d4a7c2e601`. It creates missing legacy tables on a fresh database when absent, then adds the Phase 1 tables; existing legacy tables are not dropped or rewritten.
- Added service tests for owner assignment, QR identity and branch-level access isolation.
- Updated Alembic to read the application's `DATABASE_URL` rather than rely on the hard-coded URL in `alembic.ini`.

**Verification still required:** run the backend test suite and apply Alembic against both a fresh PostgreSQL database and a disposable copy of the existing database before merging or deploying. The connected GitHub session did not provide a runnable CI result for this branch, so no passing test result is claimed.


## Phase 2 implementation status

Implemented on `feature/qless-phase-2` (draft PR #49):

- Added business-level menu categories and menu items.
- Added branch-level menu availability and optional price overrides; the branch public menu resolves the permanent branch QR.
- Added unified `POST /orders/branch` for remote preorders (selected `branch_id`) and onsite QR orders (permanent `branch_qr_token`).
- Server-side order creation validates branch/business/menu state, computes prices from the database and stores immutable item-name and unit-price snapshots.
- Added fulfillment selection for `self_collection` and `external_rider`; the latter represents a customer-arranged rider and does not imply Qless dispatch.
- Added guest checkout with customer contact details and a high-entropy access token stored only as a SHA-256 hash. Guest tokens can authorize Paystack payment initialization.
- Added branch-scoped order listing and Phase 2 API documentation.
- Added schema-level tests for remote/onsite order payloads and quantity limits.
- Added Alembic revision `b2e6c19a7d41`; legacy store/product endpoints remain in place and legacy records are not automatically backfilled.

**Verification still required:** run backend tests, import/compile checks, and both fresh-database and disposable-existing-database migration tests. No CI/test or live PostgreSQL migration success is claimed. Before deployment, also verify Paystack guest payment initialization/webhook flow end-to-end. Phase 3 still owns payment event idempotency/reconciliation and strict provider verification; Phase 4 owns kitchen workflow/realtime; Phase 5 owns the temporary single-use collection credential.


## Phase 3 implementation status

Implemented on `feature/qless-phase-3` (draft PR planned):

- Kept payment state separate from order fulfillment state. A payment can only mark an order paid after a server-side Paystack verification confirms reference, amount and currency.
- Added an authenticated customer/guest `POST /payments/verify` endpoint. Guest token validation is shared with initialization and handles timezone-aware expiry safely.
- Reworked webhook handling: HMAC-SHA512 signature validation remains over the raw body; charge-success payloads are independently verified against Paystack; canonical JSON SHA-256 event fingerprints and a unique provider/event key prevent duplicate processing.
- The Celery fallback now calls the same provider verification/reconciliation service instead of trusting status alone.
- Repeated payment initialization reuses persisted checkout authorization data when available.
- Added payment status history, webhook event records and refund ledger models.
- Added partial/full Paystack refund initiation with remaining-balance reservation, unique refund references, refund webhook updates and explicit reconciliation for uncertain outcomes.
- Added configurable `PAYMENT_CURRENCY` (default `NGN`), migration `c7a4d91e2f60`, payment API docs and verification invariant tests.
- Updated the legacy order/payment end-to-end test to assert provider-verified success and duplicate webhook handling.

**Verification still required:** no local test suite or PostgreSQL migration has been executed in this environment. Test the complete suite and migration on fresh and disposable-existing PostgreSQL databases. Paystack test-mode refund/webhook behavior must also be exercised before production.