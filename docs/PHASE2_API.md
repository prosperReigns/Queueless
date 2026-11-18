# Phase 2 API — Menus and branch-aware ordering

All routes are under `/api/v1`.

## Business menu management

- `POST /businesses/{business_id}/menu/categories` — owner/franchise administrator creates a category.
- `POST /businesses/{business_id}/menu/items` — owner/franchise administrator creates a business-level menu item with a base price and category.
- `PATCH /branches/{branch_id}/menu/items/{item_id}` — owner, franchise administrator or branch manager overrides availability and/or price for one branch.
- `GET /public/businesses/{business_slug}/branches` — public list of active branches for preorder discovery.\n- `GET /public/branches/{branch_id}/menu` — public menu for a selected branch during remote preorder.\n- `GET /public/branches/resolve/{branch_qr_token}/menu` — public menu for the branch represented by its permanent QR code.

The menu item is defined once at business scope. A branch can hide it or override its price without changing other branches. If no branch override exists, the business base price and availability apply.

## Unified order creation

### Remote preorder

`POST /orders/branch`

```json
{
  "branch_id": "BRANCH_UUID",
  "source": "preorder",
  "fulfillment_method": "self_collection",
  "scheduled_for": "2026-11-19T13:30:00+01:00",
  "customer_name": "Ada Customer",
  "customer_email": "ada@example.com",
  "customer_phone": "+2348012345678",
  "items": [
    {"menu_item_id": "MENU_ITEM_UUID", "quantity": 2}
  ]
}
```

### Onsite QR order

The customer scans the permanent branch QR. The client sends the resolved branch token, not a collection credential:

```json
{
  "branch_qr_token": "BRANCH_QR_UUID",
  "source": "onsite_qr",
  "fulfillment_method": "self_collection",
  "customer_name": "Ada Customer",
  "customer_email": "ada@example.com",
  "customer_phone": "+2348012345678",
  "items": [
    {"menu_item_id": "MENU_ITEM_UUID", "quantity": 1}
  ]
}
```

Both payloads are processed by the same branch order service. The server resolves the branch, checks active menu items and branch overrides, calculates prices from database values, and stores item-name and unit-price snapshots. Client-supplied prices are not accepted.

For a guest order, the response contains `guest_access_token`. Store it securely; it expires after 24 hours. Submit it to `POST /payments/initiate` as `guest_access_token` to authorize payment. Authenticated customers use their bearer token instead. The token is stored as a SHA-256 hash on the order.

## Branch operations

- `GET /branches/{branch_id}/orders` — authenticated member of that branch or business can list its orders. Supports `status`, `skip`, and `limit`.

## Fulfillment options

- `self_collection`: customer collects from the branch.
- `external_rider`: customer-arranged external rider collects from the branch.

Qless does not assign or dispatch riders in this phase. A separate short-lived, single-use collection credential is intentionally not implemented here; the permanent branch QR is only for menu entry and branch identification.

## Migration and compatibility

Alembic revision `b2e6c19a7d41` adds menu tables and nullable branch/guest order metadata while preserving existing store-based order rows. Legacy product/order endpoints remain available. Existing `stores` and `products` are not automatically mapped into the new business menu; that data backfill must be separately designed and verified.

## Important implementation boundary

Payment initialization can now authorize guest orders with the returned guest token. Payment verification/idempotency improvements and fully separate payment/order state are Phase 3. Kitchen transitions and realtime branch queues are Phase 4. Collection credentials and handoff are Phase 5.
