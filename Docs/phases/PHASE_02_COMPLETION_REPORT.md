# Phase 2 — Completion Report

**Phase:** [`PHASE_02_AUTH.md`](PHASE_02_AUTH.md) — Identity & Organization Platform
**Status:** Implemented by Claude. Awaiting founder manual test and CTO review (Engineering Handbook §4 lifecycle) before being marked complete in [`01_PROJECT_MASTER.md`](../01_PROJECT_MASTER.md).
**Date:** 2026-07-28

---

## 1. Session/auth architecture decision (read this first)

The phase document specifies Google OAuth login and a JWT + refresh-token session, but leaves the concrete mechanics open. Two genuinely different, defensible architectures were possible — a server-side Authorization Code redirect flow, or a client-side Google Identity Services (GSI) flow with `POST /auth/login` — and the phase document's own signals pointed in different directions (the literal `POST /auth/login` endpoint shape vs. `GOOGLE_CLIENT_SECRET` already being provisioned in Phase 1). Asked directly, the founder chose **client-side Google Identity Services**. This is now recorded as **[ADR-013](../03_ARCHITECTURE_DECISIONS.md#adr-013-phase-2-session-strategy--client-side-google-identity-services-short-lived-jwt--rotating-httponly-refresh-cookie)**, which also documents the session-token strategy built on top of it:

- Short-lived JWT **access token** (15 min default) — returned in the response body, kept only in frontend memory, never `localStorage`, never a cookie.
- Opaque, rotating **refresh token** (30 days default) — `httpOnly` + `SameSite=Lax` cookie scoped to `path=/v1/auth`; only its SHA-256 hash is ever persisted; reuse of an already-rotated-out token revokes the entire token family and is audit-logged as a theft signal.
- Phase 2's Google sign-in is **identity-only** — no Drive scopes, no offline access. Phase 3's Workspace Connector is a **separate**, server-side OAuth interaction for Drive access; this phase does not preempt or design against it.

## 2. Repository changes

```text
apps/backend/app/
  infrastructure/db/models/       Organization, Role (+RoleName enum), User, RefreshToken, AuditLog
  infrastructure/db/repositories/ One repository per model — Organization/User/Role/RefreshToken/AuditLog
  infrastructure/auth/
    jwt.py                          create_access_token / decode_access_token (HS256, typed claims)
    tokens.py                       generate_refresh_token, hash_refresh_token (SHA-256), generate_oauth_state
    google_identity.py              GoogleIdentityVerifier — the only module that imports `google-auth`
  application/
    auth_service.py                 complete_google_login, refresh_session, logout — owns its own commits
    organization_service.py         rename — owns its own commit
  presentation/
    dependencies/
      auth.py                        get_current_user, require_role(*roles) — Handbook §13.1 authn/authz split
      rate_limit.py                   Redis fixed-window limiter, fails open on Redis outage
      services.py                     get_auth_service / get_organization_service (DI providers, testable)
    api/v1/
      auth.py                         POST /auth/login, /auth/refresh, /auth/logout
      users.py                        GET /users/me
      organizations.py                GET/PATCH /organizations/current
      schemas.py                      Pydantic response/request DTOs shared across the three routers
  alembic/versions/0002_identity_tables.py   organizations, roles (seeded), users, refresh_tokens, audit_logs

packages/shared/vault_shared/errors.py   + ForbiddenError (403), RateLimitExceededError (429)
packages/shared/vault_shared/settings.py + jwt/session/Google settings (access/refresh token lifetimes,
                                            cookie name, cookie_secure, google_client_id/secret)

apps/frontend/src/
  lib/session.ts                    neutral token holder + refresh-handler registry (breaks the
                                     api-client ↔ auth-store circular-import problem)
  lib/api-client.ts                 Authorization header injection, credentials:"include", automatic
                                     401-refresh-retry-once (skipped for /v1/auth/* itself)
  lib/google-identity.ts            waits for the GSI <script> tag to finish loading
  stores/auth-store.ts              Zustand: status/user, initialize/loginWithGoogle/logout
  components/google-sign-in-button.tsx
  routes/
    index.tsx                        redirect-only: → /dashboard or /login based on auth status
    login.tsx, dashboard.tsx, profile.tsx, organization.tsx, unauthorized.tsx
  types/google-identity.d.ts        ambient types for the GSI script (no npm package exists)

packages/types/src/auth.ts          UserProfile, Organization, OrganizationUpdateRequest, AuthSession,
                                     GoogleLoginRequest — mirrors app/presentation/api/v1/schemas.py

tests/unit/backend/                 8 new files, 44 new tests (jwt, tokens, google_identity, rate_limit,
                                     auth_dependencies, auth_router, users_router, organizations_router)
tests/unit/backend/factories.py     transient (session-less) Organization/Role/User builders for tests
tests/integration/backend/test_auth_service_integration.py   7 tests against a real Postgres — provisioning,
                                     login reuse, email conflict, refresh rotation, reuse-detection revokes
                                     the whole family, logout, org rename
apps/frontend/src/lib/session.test.ts, api-client.test.ts (extended), stores/auth-store.test.ts,
                                     components/google-sign-in-button.test.tsx   18 new frontend tests
```

## 3. Database changes

Migration `0002_identity_tables` (on top of Phase 1's `0001_enable_pgcrypto`): `organizations`, `roles` (seeded with `owner`/`admin`/`member`), `users` (FK organization + role, unique `google_sub`/`email`), `refresh_tokens` (FK user, unique `token_hash`, self-referential `replaced_by_id` for the rotation chain), `audit_logs` (nullable FK organization/user, `metadata` JSONB — Python attribute named `metadata_` since `metadata` is reserved on SQLAlchemy's declarative `Base`).

**Design simplification, noted for CTO review:** the phase document listed `UserRole` as an entity "if your model requires it." Since a user belongs to exactly one organization and holds exactly one role in this phase's model (no multi-org membership yet), a join table isn't needed — `User` has direct `organization_id`/`role_id` foreign keys instead. `Role` still exists as its own seeded table (not an enum-only column) so its literal presence in the phase spec is honored, and so a future phase can extend it (permissions, custom roles) without a migration that introduces the table from scratch.

## 4. API surface

```text
POST   /v1/auth/login       { id_token }              → SessionResponse (+ Set-Cookie refresh token)
POST   /v1/auth/refresh     (refresh cookie)           → SessionResponse (+ rotated Set-Cookie)
POST   /v1/auth/logout      (refresh cookie, optional)  → 204, clears cookie

GET    /v1/users/me                                    → UserProfileResponse

GET    /v1/organizations/current                        → OrganizationResponse
PATCH  /v1/organizations/current   { name }  (owner/admin only) → OrganizationResponse
```

Every error response uses the same envelope Phase 1 established (`{"error": {"code", "message", "details"}}`) — `ForbiddenError` (403) and `RateLimitExceededError` (429) are new additions to `vault_shared`'s typed-error hierarchy, both handled generically by the existing exception handler with no new wiring needed.

## 5. Tests and what was actually verified in this environment

- **Backend:** 62 unit tests total (44 new for Phase 2) + 7 new integration tests (skip locally, run in CI against a real Postgres/Redis service container — same pattern as Phase 1). `ruff`/`mypy` clean across 48 source files.
- **Frontend:** 28 vitest tests total (18 new) covering the session module, api-client's auth-header/retry/credential behavior, the auth store's four actions, and the Google button's missing-config state. `eslint`/`tsc`/`vite build` all clean.
- **Live, not just mocked:** started the real `uvicorn` server and hit the auth endpoints with `curl` — confirmed `/users/me` and `/organizations/current` correctly return 401 without a token, `/auth/refresh` correctly returns 401 without a cookie, a malformed login body returns a 422 with the exact Pydantic field error, and — notably — **`POST /auth/login` with a bogus ID token made a real network call to Google's public-key endpoint and correctly rejected it**, confirming the `google-auth` verification path works end-to-end against the real Google service, not just against the mocked verifier used in unit tests.
- **Not verified in this environment:** the actual Google Identity Services button (needs a real `GOOGLE_CLIENT_ID`/`VITE_GOOGLE_CLIENT_ID` and a browser); the 7 new integration tests against a live Postgres; the full `docker compose up` stack — same Docker/Postgres limitation noted in the Phase 1 report (this sandbox's Docker Desktop can't run on the host macOS version).

**Concrete manual-test steps for the founder**, beyond Phase 1's checklist: create a Google Cloud OAuth Client ID (Console → APIs & Services → Credentials, application type "Web," authorized JavaScript origin `http://localhost:5173`), set `GOOGLE_CLIENT_ID` in the root `.env` and `VITE_GOOGLE_CLIENT_ID` in `apps/frontend/.env` to the same value, run `docker compose up`, and click through: sign in → land on `/dashboard` → visit `/profile` and `/organization` → rename the organization → refresh the page (session recovery) → log out → confirm `/dashboard` redirects to `/login`.

## 6. Known limitations / follow-ups

- Same `packages/types` manual-sync caveat as Phase 1 (ADR-012), now also covering `auth.ts`.
- No live Postgres/Redis/Docker verification in this environment (see §5) — same gap as Phase 1, not newly introduced.
- Google sign-in has never been exercised against a real Google account in this environment — no OAuth client was available to provision here.
- Phase 2's Google sign-in is identity-only (see §1) — Phase 3 needs its own, separate OAuth design for Drive access; do not assume Phase 2's flow covers it.

## 7. Recommendation for Phase 3

The Google Workspace Connector Platform (`Docs/phases/PHASE_03_STORAGE_SCANNER.md`) can build directly on this foundation: `get_current_user`/`require_role` are ready to protect connector endpoints, `organization_id` is already the tenant key on every identity table, and the audit-log pattern (`AuditLogRepository.record`) is established and ready to extend to connector events (connection attempts, token refresh, disconnects) exactly as that phase's spec calls for.
