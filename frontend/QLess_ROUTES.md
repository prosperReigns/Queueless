# Qless Frontend Route and Interface Plan

This file describes the target route groups for the existing React + TypeScript + Vite application. It does not require splitting the frontend into separate deployments.

## Shared application shell

- Public discovery and branch menu pages
- Authentication and account recovery
- Shared API client, session/auth context, query cache and notification services
- Role-aware navigation; server remains authoritative for permissions

## Customer routes

- `/` — restaurant discovery
- `/businesses/:businessId` — business profile and branch list
- `/branches/:branchId` — branch menu
- `/q/:branchToken` — resolve permanent branch QR and open branch menu
- `/cart`, `/checkout`
- `/orders/:orderId`, `/orders/:orderId/confirmation`, `/orders`
- `/account`

Support guest checkout where the business policy permits it. Customer ordering must record `preorder` or `onsite_qr` origin and `self_pickup` or `external_rider` fulfillment.

## Merchant management routes

- `/manage` — business overview
- `/manage/businesses/:businessId` — business settings
- `/manage/businesses/:businessId/branches` — branch list and setup
- `/manage/branches/:branchId` — branch overview
- `/manage/branches/:branchId/menu` — menu, branch overrides and availability
- `/manage/branches/:branchId/orders` — order management
- `/manage/staff` — memberships and role assignment
- `/manage/reports` — business/franchise reports

A franchise administrator sees authorized branches. A branch manager sees only assigned branches.

## Kitchen display routes

- `/kitchen/:branchId` — branch kitchen queue
- Incoming/new, accepted, preparing and ready columns
- Ticket detail, item notes, elapsed preparation time and priority
- Large touch-friendly controls; no customer checkout navigation in this layout

## Fulfillment routes

- `/fulfillment/:branchId` — collection desk
- `/fulfillment/verify` — scan or enter a collection PIN
- `/fulfillment/orders/:orderId` — authorized handoff detail

Only a valid, paid, ready order with an unexpired credential can be released. Collection authorization is distinct from the permanent branch QR.

## Migration from current routes

Keep the existing `/stores`, `/dashboard/merchant`, product and order routes available while their APIs are backed by the compatibility layer. Migrate navigation gradually after the business/branch and membership APIs are in place. Do not rely on frontend route guards for tenant isolation.
