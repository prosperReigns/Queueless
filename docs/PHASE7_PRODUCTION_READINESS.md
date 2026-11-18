# Phase 7 — Production Readiness and Platform Hardening

## Goal

Harden the Phase 1–6 Qless implementation for a controlled production pilot. This phase adds operational probes, automated regression coverage and operator runbooks. It does **not** certify the service as production-ready: provider, infrastructure, restore and load tests must still be executed in the target environment.

## Scope and implementation

### 1. Health and deployment probes
- Preserve the existing `GET /health` response for backwards compatibility.
- Add `GET /health/live` as a process-liveness probe. It must not depend on external services.
- Add `GET /health/ready` as a database-readiness probe. It performs a bounded, read-only `SELECT 1`; on failure it returns HTTP 503 and a sanitized dependency status (never connection details or credentials).
- Configure the platform load balancer to use readiness for traffic admission and liveness for process restart decisions. Do not use a deep dependency probe as a liveness probe.

### 2. Tenant isolation and security regression checks
- Keep tenant authorization in backend dependencies/services; frontend route visibility is not a security boundary.
- Exercise global business membership, branch-scoped membership, cross-branch denial, inactive membership denial and business boundary denial.
- Keep collection credentials high-entropy, hashed at rest, branch-bound, expiring and atomically single-use.
- Keep Paystack signature verification, server-side amount/currency/reference verification and idempotent event handling mandatory.
- Never log authorization headers, guest tokens, payment secrets, PINs, QR credential payloads or full provider payloads.

### 3. Payment reconciliation operations
- Use the authenticated payment/refund reconciliation endpoints and provider verification service; never mark a payment successful from a browser callback alone.
- Reconcile against Paystack transaction references and refund references. Investigate uncertain provider outcomes before retrying an action.
- Daily operator reconciliation should compare provider transactions/refunds with Qless payment/refund records and bank settlement reports. Record discrepancies and resolution references.
- Refunds, fees, taxes and net settlement remain distinct from the Phase 6 gross-order operational report; do not present gross order value as revenue or settlement.

### 4. Database backup and recovery
- Use managed PostgreSQL automated backups with point-in-time recovery where available. For self-managed PostgreSQL, schedule encrypted `pg_dump -Fc` backups and retain off-host copies.
- Store backup encryption keys separately from the backup destination. Restrict backup access to operators.
- Before every migration, take a verified backup and record the current Alembic revision.
- Restore into a separate database first; verify schema revision, row counts and representative order/payment/refund/fulfillment records before considering a recovery complete.
- Set and test explicit RPO/RTO targets with the business owner. A backup job is not proven until a restore drill succeeds.

Example backup (run from a trusted host; provide credentials through `PGSERVICE` or `PGPASSWORD`, never commit them):
```bash
pg_dump --format=custom --no-owner --file="qless-$(date -u +%Y%m%dT%H%M%SZ).dump" "$DATABASE_URL"
pg_restore --list "qless-YYYYMMDDTHHMMSSZ.dump" >/dev/null
```

Example restore to a **new, empty recovery database** (do not point this at production):
```bash
createdb qless_restore_drill
pg_restore --no-owner --clean --if-exists --dbname=qless_restore_drill "backup.dump"
```

### 5. Deployment and secrets
- Deploy immutable commits; run CI before deployment and keep a rollback target.
- Apply Alembic migrations as a separate, controlled release step. Do not run migrations automatically in every web-worker startup.
- Keep `JWT_SECRET_KEY`, `SECRET_KEY`, Paystack credentials, database credentials and Firebase/Termii secrets in the hosting provider's secret manager. Rotate compromised credentials and never place production values in `.env.example`.
- Set an explicit production `FRONTEND_ORIGIN`, restrictive CORS allowlists and HTTPS URLs. Do not use wildcard origins with credentialed requests.
- Use separate least-privilege database credentials for application runtime and migration execution where supported.
- Confirm the frontend API/websocket base URLs, Paystack callback URL and webhook URL are production URLs before enabling live payments.

### 6. Monitoring and incident response
- Collect JSON application logs with request IDs; propagate `X-Request-ID` to support investigations.
- Alert on elevated HTTP 5xx rates, readiness failures, database connection exhaustion, Redis/rate-limit failures, queue backlog, failed payment verification and refund states requiring attention.
- Correlate payment/order identifiers in restricted operational logs, but do not log tokens, credentials, card data or customer secrets.
- On a payment incident: preserve provider event/reference, check Qless payment and event records, verify directly with Paystack, then reconcile. Never manually edit payment status as the first response.
- On a suspected tenant leak: disable affected access, preserve audit/log evidence, identify impacted business/branch IDs, rotate exposed credentials and notify affected parties according to applicable obligations.

### 7. Load and resilience validation
Run a representative staging test before launch. Include customer discovery/menu reads, concurrent order creation, payment callback/webhook retries, kitchen queue polling, WebSocket reconnect/replay and simultaneous collection credential redemption.
Measure p50/p95/p99 latency, 4xx/5xx rate, DB pool wait, CPU/memory, Redis health, worker backlog and provider timeout rate. Test graceful shutdown and restart during in-flight requests. Establish numeric limits from the actual hosting plan and expected pilot traffic rather than guessing universal thresholds.

## Release checklist

- [ ] Phase 6 PR #53 is merged or Phase 7 is rebased onto its final merged commit before release.
- [ ] Backend tests, frontend lint and frontend production build pass in GitHub Actions.
- [ ] Full Alembic chain succeeds on a fresh PostgreSQL database.
- [ ] Full Alembic chain succeeds on a disposable copy of existing data; legacy records remain readable.
- [ ] Cross-business, cross-branch and inactive-membership access tests pass.
- [ ] Paystack test-mode success, failure, duplicate webhook, timeout/retry, refund and refund reconciliation scenarios pass.
- [ ] Simultaneous collection redemption permits exactly one successful redemption.
- [ ] Backup is encrypted/off-host and a restore drill has been completed.
- [ ] Readiness/liveness probes are configured in the hosting platform.
- [ ] Production secrets, CORS, HTTPS, callbacks and webhook URLs are reviewed.
- [ ] Staging load/resilience test has recorded results and accepted thresholds.
- [ ] Rollback owner, on-call contact and incident procedures are documented.

## Explicitly not completed by repository changes alone

No live PostgreSQL migration, Paystack live/test transaction, backup restore, production deployment, security penetration test, load test or monitoring integration is performed by this code change. These are environment-dependent release gates and must be evidenced before launch.
