# 08 — Security Guide

Status: **Reference document**, introduced in Phase 10 (ADR-022) as the consolidated write-up of a security review conducted across the whole codebase. Security *decisions* with real trade-offs are logged as ADRs (see the [ADR log](03_ARCHITECTURE_DECISIONS.md)); this document is the checklist-style summary of what's in place, where, and what's explicitly deferred.

---

## 1. Authentication & session handling

- **Identity:** Google Identity Services (client-side sign-in), verified server-side against `GOOGLE_CLIENT_ID` as the expected audience. See ADR-013.
- **Sessions:** short-lived JWT access token (15 min default) + a rotating, `httpOnly`, `Secure`-in-production refresh cookie (30 days default). A stolen access token is useless after 15 minutes; a stolen refresh cookie can't be read by JavaScript at all.
- **JWT validation:** signature (HMAC, `JWT_SECRET` ≥32 bytes — the Settings default is padded specifically so PyJWT's own weak-key warning doesn't fire even in local dev, though the real value must still come from a real secret in any deployed environment), expiry, and issuer are all checked on every request (`app/presentation/dependencies/auth.py`). Verified by `tests/unit/backend/test_jwt.py` — including an explicit test that a token signed with a *different* secret is rejected.
- **Logout:** revokes the refresh token server-side (not just clearing the client cookie) — a stolen-but-not-yet-used refresh cookie is invalidated the moment the legitimate user logs out.

## 2. Authorization

- **RBAC:** `owner` / `admin` / `member`, enforced via `require_role(...)` FastAPI dependencies on every mutating endpoint. Read endpoints use `get_current_user` only, scoped to that user's own organization.
- **Organization isolation:** every query that returns organization-scoped data filters by `organization_id` taken from the authenticated user's own token — never from a client-supplied path/query/body parameter. Verified across every phase's own test suite (each new resource type ships a test asserting cross-org access returns 404, not the other org's data).
- **The Approval System as the last authorization gate before a real mutation** (Phase 8, ADR-020; extended by Phase 9, ADR-021): no code path — human or policy-driven — reaches a live Google Drive write without first passing through `validate_execution_permissions` and producing an audited `ApprovalDecision`.

## 3. Encryption

- **At rest:** OAuth connector tokens are Fernet-encrypted before being written to `connector_credentials` (`CONNECTOR_ENCRYPTION_KEY`, ADR-014) — the database itself being compromised does not hand over live Drive access. In AWS, RDS storage encryption is also enabled at the infrastructure layer (`infrastructure/terraform/modules/database`).
- **In transit:** `DATABASE_URL` uses `sslmode=require` in the Terraform-provisioned environments; ElastiCache Redis has `transit_encryption_enabled = true`; the ALB terminates TLS 1.2+ only (`ELBSecurityPolicy-TLS13-1-2-2021-06`) with an HTTP→HTTPS redirect on port 80.
- **`cryptography` 50.0.0** (bumped from 49.0.0 in Phase 10 to clear CVE-2026-69247 — a PKCS7 decrypt timing/error oracle not reachable through this codebase's Fernet-only usage, but fixed regardless; see ADR-022).

## 4. Secret management

Every secret lives in an environment variable, documented (never with a real value) in `.env.example`. In AWS, each becomes its own Secrets Manager entry (`infrastructure/terraform/modules/secrets`), resolved into ECS task environments at container start — never baked into an image, never in a task definition's plaintext, never in Terraform state in a way this project's own code controls (state itself must be encrypted at the backend level — see `environments/*/backend.tf`'s comment). `gitleaks` runs in CI on every PR (Phase 10) to catch an accidentally-committed secret before merge.

## 5. Rate limiting

Fixed-window, Redis-backed, fails open on a Redis outage (defense-in-depth, never the primary control — JWT/RBAC are). Applied to: auth login/refresh, every job-starting endpoint (scan/enrichment/embedding/recommendation-refresh/workflow-manual-trigger), every AI-Gateway-backed endpoint (search, conversation ask), the connector OAuth handshake (connect + callback), and both approval-decision endpoints (Phase 10, ADR-022 — closing a gap Phase 8 explicitly left open). See `app/presentation/dependencies/rate_limit.py`.

## 6. Input validation & output sanitization

- **Input:** every request body is a Pydantic v2 model — type/shape validation happens before a handler function body ever executes; a malformed request never reaches application code. UUIDs, enums, and numeric ranges are validated at the schema layer, not re-checked ad hoc per endpoint.
- **Output:** structured JSON only, via FastAPI's own response-model serialization — no template rendering, no raw HTML construction anywhere in this API (the frontend is a separate SPA that consumes JSON). Nothing in this codebase interpolates user input into a shell command, SQL string, or file path — every DB query goes through SQLAlchemy's parameterized query builder, every subprocess call in `infrastructure/scripts/` takes fixed arguments, not user input.

## 7. CORS

`allow_origins` is the configured `CORS_ALLOW_ORIGINS` list (never `*`), `allow_methods`/`allow_headers` are explicit lists (Phase 10 tightened these from `["*"]`), `allow_credentials=True` (required for the refresh cookie to work cross-origin in dev). Reviewed and confirmed still correct in Phase 10 — no change to the actual origin-allowlisting logic, only to the methods/headers lists.

## 8. Dependency vulnerability scanning

`pip-audit` (backend + worker) and `pnpm audit` run in CI's `security` job on every PR (Phase 10 — new this phase). Two real CVEs were found and fixed in the codebase's existing dependencies on the first run: `cryptography` 49.0.0 → 50.0.0, `pypdf` 5.9.0 → 6.14.2 (see ADR-022 for detail on both). `aquasecurity/trivy-action` scans the three built Docker images for OS-package CVEs in CI's `docker-build` job.

## 9. Security headers

`app/core/security_headers_middleware.py` (Phase 10) adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, a restrictive `Permissions-Policy`, and a `Content-Security-Policy` (locked to `default-src 'none'` for the API, a scoped policy for `/v1/docs`'s Swagger UI assets). `Strict-Transport-Security` is sent only when `cookie_secure` is true (i.e., only in an environment actually served over HTTPS — sending it over plain HTTP would be a harmless no-op the browser ignores, but the code doesn't pretend otherwise).

## 10. Audit log integrity

`AuditLog`, `ExecutionAudit`, and every `*_events`/`*_progress` table are insert-only by construction — no repository in this codebase exposes an `update`/`delete` method for any of them, and no API endpoint exposes one either. This is enforced by the absence of the capability, not by a database permission grant (a `REVOKE UPDATE, DELETE` at the database-role level is a natural follow-up for a real production deployment, tracked as a known limitation below).

## 11. Threat model review

| Surface | Primary risk | Mitigation |
|---|---|---|
| Authentication | Token theft/replay | Short-lived access token, `httpOnly` rotating refresh cookie, revocation on logout |
| Connectors (OAuth) | Authorization-code interception, state-forgery | `state` parameter with TTL (`OAUTH_STATE_TTL_SECONDS`), server-side code exchange (never client-side) |
| Execution | Unauthorized/accidental Drive mutation | Approval System is the sole path to a mutating call; permission re-validated at execution time, not just at plan-creation time (real time passes between approval and execution) |
| Workflows/Automation | Automation bypassing human oversight | A policy is a second *kind* of approver, never a bypass — every auto-execution produces the same audited `ApprovalDecision` a human's would (ADR-021) |
| AI interactions | Prompt injection via file content reaching a completion provider | The current completion provider is stubbed/deterministic (no real LLM call exists yet to inject into); revisit this row the day a real provider is wired in — see Known Issues |

## 12. Known limitations / deferred items

- Database-role-level `REVOKE` on audit tables (currently enforced only by application code never calling update/delete).
- Prompt-injection-specific mitigations (out of scope while the completion provider is stubbed — see §11).
- Per-file (not per-recommendation) policy conditions for automated execution (ADR-021's own documented scope boundary).
- CSP is `'none'`-based for the API (correct, since it serves JSON only) — revisit if the API ever serves any HTML/rendered content directly.
