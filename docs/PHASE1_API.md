# Qless Phase 1 API

Base path: `/api/v1`. All endpoints except the branch QR resolver require a valid access token.

## Business

- `POST /businesses` — create an independent restaurant or franchise. The authenticated user automatically receives the `owner` membership.
- `GET /businesses` — list businesses where the current user has an active membership.
- `GET /businesses/{business_id}` — retrieve an accessible business.
- `PATCH /businesses/{business_id}` — update business details; owner or franchise administrator only.

Create payload:
```json
{
  "name": "Ada Kitchen",
  "business_type": "independent",
  "description": "Nigerian meals",
  "email": "hello@example.com",
  "phone": "+234..."
}
```

Allowed `business_type`: `independent`, `franchise`.

## Branches

- `POST /businesses/{business_id}/branches` — owner/franchise administrator creates a branch.
- `GET /businesses/{business_id}/branches` — business administrators see all branches; branch staff see only assigned branches.
- `GET /branches/{branch_id}` — retrieve a branch only when the user is assigned to it or has business-level membership.
- `PATCH /branches/{branch_id}` — owner, franchise administrator or branch manager.

A branch defaults to country `NG` and timezone `Africa/Lagos`, both configurable.

## Staff memberships

- `POST /businesses/{business_id}/memberships` — assign an existing active Qless user.
- `GET /businesses/{business_id}/memberships` — list memberships; owner/franchise administrator only.

Roles:
- Business scope (`branch_id: null`): `owner`, `franchise_admin`.
- Branch scope (requires `branch_id`): `branch_manager`, `cashier`, `kitchen_staff`, `collection_staff`.

The creator becomes owner automatically. Staff assignment cannot create another owner. Only the owner of a franchise can appoint a franchise administrator. Branch-level memberships are checked against the requested branch on the backend.

Example staff assignment:
```json
{
  "user_id": "existing-user-uuid",
  "role": "kitchen_staff",
  "branch_id": "branch-uuid"
}
```

## Permanent branch QR

- `GET /branches/{branch_id}/qr` — authorized staff retrieves the branch QR token and customer-facing menu URL.
- `GET /public/branches/resolve/{token}` — public resolver used when a customer scans the branch QR.

The branch QR identifies a location and opens its menu. It does **not** authorize collection of an order. Order collection credentials will be designed and implemented in the fulfillment phase.

## Migration

The Phase 1 Alembic revision is `91d4a7c2e601`. It creates the existing legacy tables on a fresh database if they are absent, then creates the new tenant tables. Existing tables are left untouched. Before production, take a database backup and inspect the actual database schema and `alembic_version` state; do not manually stamp a revision unless the schema has been verified.

Configure `DATABASE_URL` in the backend environment. Alembic now reads the same setting as the application rather than using a hard-coded local database URL.

Run from `backend/`:
```bash
alembic upgrade head
pytest -q
```
