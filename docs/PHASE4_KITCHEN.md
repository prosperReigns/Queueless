# Phase 4 — Kitchen operations and realtime

Phase 4 introduces a branch-scoped kitchen display workflow. It does not implement customer collection, rider handoff or dispatch; those remain Phase 5.

## Ticket lifecycle

A kitchen ticket is created only after the order's payment has been independently verified by the Phase 3 Paystack flow. One ticket is allowed per order. The ticket progresses strictly:

`NEW → ACCEPTED → PREPARING → READY`

Payment status remains separate from kitchen status. The parent order remains `PAID` during kitchen processing; Phase 5 owns collection and fulfillment states.

## API

- `GET /api/v1/branches/{branch_id}/kitchen/queue` — authenticated branch queue.
- `PATCH /api/v1/kitchen/tickets/{ticket_id}/status` — advance one legal ticket state.
- `GET /api/v1/branches/{branch_id}/kitchen/events?after_id=0` — durable event replay/polling fallback.
- `WS /api/v1/ws/kitchen/{branch_id}?token=...&after_id=0` — realtime event stream; reconnect using the last event id.

Kitchen access is limited to platform admins and branch/business memberships with owner, franchise-admin, branch-manager or kitchen-staff roles. Cashier and collection-staff memberships cannot access the kitchen queue. Branch scoping is enforced server-side on every HTTP request and during the WebSocket session.

## Reliability

Ticket creation and its `ticket.created` event are committed in the same database transaction as the verified payment/order update. Ticket state changes and their event records are also committed together. Events have monotonically increasing database IDs, so clients can replay missed updates after reconnecting. WebSockets only transport persisted events; the database event log is the source of truth. Clients can use the HTTP events endpoint when WebSockets are unavailable.

## Migration and verification

Alembic revision: `d4b8e1a6c903` (parent `c7a4d91e2f60`). It adds kitchen tickets and the durable event log without altering legacy store orders or payment records.

Run from `backend/`:

```bash
python -m compileall app tests
pytest -q
alembic upgrade head
```

Apply the migration first to a fresh PostgreSQL database and then to a disposable copy of the current database. No test or database migration result is claimed until those commands have actually completed.
