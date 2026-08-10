# Phase 3 — Completion Report

**Phase:** [`PHASE_03_STORAGE_SCANNER.md`](PHASE_03_STORAGE_SCANNER.md) — Google Workspace Connector Platform
**Status:** Implemented by Claude. Awaiting founder manual test and CTO review (Engineering Handbook §4 lifecycle) before being marked complete in [`01_PROJECT_MASTER.md`](../01_PROJECT_MASTER.md).
**Date:** 2026-07-28

---

## 1. Connector OAuth architecture (read this first)

This phase needed the exact flow Phase 2's ADR-013 deliberately deferred: a durable, refreshable, offline-capable connection to a Google Workspace account, for future Drive access (Phase 4's scanner) — not a per-user identity check. The phase document's API scope literally lists both the initiate and callback endpoints as `POST`, which only makes sense if Google's redirect lands on a **frontend** route that then POSTs the code/state to the backend, rather than the backend hosting a callback Google redirects to directly. This is now recorded as **[ADR-014](../03_ARCHITECTURE_DECISIONS.md#adr-014-phase-3-google-workspace-connector--server-side-authorization-code-flow-with-a-frontend-hosted-callback-encrypted-token-storage)**:

- `POST /v1/connectors/google/connect` → generates a single-use, Redis-backed, org-bound OAuth state → returns `{ authorize_url }` → frontend does a real top-level navigation to Google.
- Google redirects to a **frontend** route (`/connectors/google/callback`), which reads `code`/`state` off its own URL and POSTs them to `POST /v1/connectors/google/callback`.
- Tokens are encrypted at rest (Fernet, reversible — unlike Phase 2's refresh tokens, these must be usable, not just comparable) and refreshed automatically and transparently by `ConnectorService.get_valid_access_token()`, the single choke point every future caller (Phase 4's scanner) must use.
- Phase 2's Google sign-in (identity-only, no Drive scope) and Phase 3's Workspace Connector (Drive-scoped, offline access) remain two genuinely separate OAuth interactions, as ADR-013 anticipated — this phase does not touch or extend Phase 2's flow.

## 2. Repository changes

```text
apps/backend/app/
  infrastructure/security/encryption.py     Fernet encrypt_token/decrypt_token — the only place
                                             OAuth tokens are encrypted/decrypted
  infrastructure/connectors/
    google_workspace.py                       GoogleWorkspaceOAuthClient — the only module that
                                               calls Google's OAuth token/userinfo/revoke endpoints
    oauth_state.py                            Redis-backed single-use OAuth state (CSRF/replay protection)
  infrastructure/db/models/
    storage_connector.py                      StorageConnector (+ ConnectorProvider, ConnectorStatus enums)
    connector_credentials.py                  ConnectorCredentials (encrypted tokens, one-to-one)
  infrastructure/db/repositories/
    storage_connector_repository.py           get/list/upsert_connected/mark_verified/mark_error/mark_disconnected
    connector_credentials_repository.py       get/upsert/update_access_token/delete
  application/connector_service.py            list_for_organization, get_owned, initiate_connect,
                                               complete_connect, get_valid_access_token, verify, disconnect
  presentation/
    dependencies/services.py                  + get_connector_service (DI provider, testable)
    api/v1/connectors.py                      GET /connectors, POST /connectors/google/{connect,callback},
                                               GET /connectors/{id}/status, POST /connectors/{id}/{verify,disconnect}
    api/v1/schemas.py                          + ConnectorResponse, InitiateConnectResponse, CompleteConnectRequest
  alembic/versions/0003_storage_connectors.py   organizations/roles/users (Phase 2) → adds
                                                 storage_connectors + connector_credentials
```

It adds `storage_connectors` (unique on organization+provider — one row per connection, reconnecting reuses the same row) and `connector_credentials` (one-to-one, encrypted `access_token_encrypted`/`refresh_token_encrypted`).

```text
packages/shared/vault_shared/errors.py    (unchanged this phase — reused ConflictError/UnauthorizedError/
                                            DependencyUnavailableError/NotFoundError from Phase 1/2)
packages/shared/vault_shared/settings.py  + google_workspace_redirect_uri, google_workspace_scopes,
                                            oauth_state_ttl_seconds, connector_encryption_key

apps/frontend/src/
  lib/connector-status.ts                 connectorStatusColor — the one piece of new pure logic,
                                           extracted specifically so it's unit-testable
  routes/
    storage-connections.tsx                 list, connect wizard, connected-account summary,
                                             disconnect confirmation, loading/error states
    connectors.google.callback.tsx          completes the OAuth exchange after Google's redirect

packages/types/src/connectors.ts          Connector, InitiateConnectResponse, CompleteConnectRequest

tests/unit/backend/                       4 new files, 34 new tests (encryption, Google Workspace OAuth
                                           client, OAuth state store, connectors router)
tests/integration/backend/test_connector_service_integration.py   7 tests against a real Postgres/Redis —
                                           full connect→verify→refresh→disconnect lifecycle, cross-org
                                           state rejection, duplicate-connect rejection, verify-marks-error
apps/frontend/src/lib/connector-status.test.ts   3 new frontend tests
```

## 3. Database changes

Migration `0003_storage_connectors` (on top of Phase 2's `0002_identity_tables`): `storage_connectors` (`organization_id` FK, `provider`, `status`, `connected_by_user_id` FK, `account_email`, `workspace_domain`, `last_verified_at`/`last_failed_at`/`last_error`, a placeholder `last_synced_at` for Phase 4, unique on `(organization_id, provider)`) and `connector_credentials` (`connector_id` FK unique, `access_token_encrypted`, `refresh_token_encrypted`, `granted_scopes`, `expires_at`).

**Design simplifications, noted for CTO review:** the phase spec listed `Provider Configuration` and `Synchronization Metadata` as entities, both explicitly scoped as placeholder/not-yet-needed. `Provider Configuration` is a code-level `Settings` concern (one global OAuth app registration via `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`, no per-tenant BYO-OAuth-app support yet) rather than a DB table with nothing to configure per-row yet. `Synchronization Metadata` is a single nullable `last_synced_at` column on `storage_connectors` rather than a dedicated table — Phase 4 is better positioned to design that table's real shape once it knows what a sync cursor actually needs to hold.

## 4. API surface

```text
GET    /v1/connectors                       (any authenticated org member)  → Connector[]
POST   /v1/connectors/google/connect        (owner/admin)                    → { authorize_url }
POST   /v1/connectors/google/callback       (owner/admin)  { code, state }    → Connector
GET    /v1/connectors/{id}/status           (any authenticated org member)  → Connector
POST   /v1/connectors/{id}/verify           (any authenticated org member)  → Connector
POST   /v1/connectors/{id}/disconnect       (owner/admin)                    → Connector
```

RBAC gating (owner/admin for connect/callback/disconnect, any member for list/status/verify) was an engineering judgment call — the phase spec's API scope didn't specify roles per endpoint. `Connector` responses never include token values (Handbook §13 / phase spec's "never expose refresh tokens") — those live only in `ConnectorCredentials`, which has no response schema at all.

## 5. Tests and what was actually verified in this environment

- **Backend:** 96 unit tests total (34 new for Phase 3) + 7 new integration tests (skip locally, run in CI against real Postgres/Redis — same pattern as Phase 1/2). `ruff`/`mypy` clean across 60 source files.
- **Frontend:** 31 vitest tests total (3 new — `connectorStatusColor`). Consistent with Phase 1/2's established scope, the route components themselves (`storage-connections.tsx`, `connectors.google.callback.tsx`) are not unit-tested — they're thin wrappers around TanStack Query/Router that would need a full router test harness for marginal benefit; they're covered by the founder's manual QA checklist instead. `eslint`/`tsc`/`vite build` all clean.
- **Live, not just mocked:** started the real `uvicorn` server and confirmed every `/v1/connectors/*` endpoint correctly returns 401 without a token — the RBAC/auth wiring is live, not just unit-tested.
- **Not verified in this environment:** the actual Google OAuth consent screen and redirect (needs a real `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` with `GOOGLE_WORKSPACE_REDIRECT_URI` authorized, and a browser); the 7 new integration tests against a live Postgres/Redis; the full `docker compose up` stack — same Docker/Postgres limitation noted in the Phase 1/2 reports.

**Concrete manual-test steps for the founder**, beyond Phase 1/2's checklist: on the same Google Cloud OAuth client used for Phase 2, add `http://localhost:5173/connectors/google/callback` as an authorized redirect URI; set `CONNECTOR_ENCRYPTION_KEY` in the root `.env` (a working local-dev key is already in `.env.example` — regenerate it for anything beyond your own machine); run `docker compose up`; sign in, go to Storage Connections, click "Connect Google Workspace," approve on Google's consent screen, confirm you land back on Storage Connections with a `connected` status and the right account email/domain shown; click Verify; click Disconnect and confirm the status changes and a re-connect works cleanly afterward.

## 6. Known limitations / follow-ups

- Same `packages/types` manual-sync caveat as Phase 1/2 (ADR-012), now also covering `connectors.ts`.
- No live Postgres/Redis/Docker verification in this environment (see §5) — cumulative gap since Phase 1.
- No real Google OAuth exercised — same category of gap as Phase 2, now blocking this phase's connect flow specifically.
- `Synchronization Metadata` is a single placeholder column, not a real table — Phase 4 should design its actual shape rather than assuming `last_synced_at` alone is sufficient.
- Route components remain outside the automated test suite by consistent design choice (see §5) — flagged as a standing item in the CTO Dashboard's Technical Debt in case a future phase's UI complexity warrants e2e coverage.

## 7. Recommendation for Phase 4

The Storage Scanner phase can build directly on this foundation: call `ConnectorService.get_valid_access_token(connector)` to get a live, always-fresh access token — never touch `connector_credentials` or `GoogleWorkspaceOAuthClient` directly. The `last_synced_at` placeholder column on `storage_connectors` is ready for the scanner to start writing to; if the scanner's actual sync-cursor needs turn out richer than a single timestamp, design a dedicated table rather than overloading that column. The `drive.readonly` scope is already granted from every connector created under this phase — no re-consent should be needed to start scanning.
