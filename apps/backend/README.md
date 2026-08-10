# apps/backend

API and application-service layer for AI Project Vault. Owns request handling, orchestration, RBAC enforcement, and the AI Gateway boundary.

Never calls an LLM provider SDK directly — all model calls route through `packages/shared`'s AI Gateway abstraction (built in Phase 6 — see [ADR-018](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-018-ai-intelligence-engine-phase-6--ai-gateway-abstraction-local-first-embeddings-mean-centered-similarity-and-a-stubbed-completion-provider)). Never talks to `apps/worker`'s internals directly; communicates only via the documented queue contracts.

FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2 (ADR-012 — not NestJS), layered per Engineering Handbook §6.1.2 (`app/presentation`, `app/application`, `app/domain`, `app/infrastructure`). Phase 1 shipped only `/health/live`, `/health/ready`, `/v1/version` — no business logic. Phase 2 added the Identity domain: Google Identity Services login (`/v1/auth/login`), JWT + rotating-refresh-cookie sessions (`/v1/auth/refresh`, `/v1/auth/logout`), RBAC (`/v1/users/me`, `/v1/organizations/current`) — see [`Docs/phases/PHASE_02_AUTH.md`](../../Docs/phases/PHASE_02_AUTH.md) and [ADR-013](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-013-phase-2-session-strategy--client-side-google-identity-services-short-lived-jwt--rotating-httponly-refresh-cookie). Phase 3 adds the Google Workspace Connector Platform: OAuth connect/callback/verify/disconnect (`/v1/connectors/*`), encrypted-at-rest tokens, automatic refresh — see [`Docs/phases/PHASE_03_STORAGE_SCANNER.md`](../../Docs/phases/PHASE_03_STORAGE_SCANNER.md) and [ADR-014](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-014-phase-3-google-workspace-connector--server-side-authorization-code-flow-with-a-frontend-hosted-callback-encrypted-token-storage) — a deliberately **separate** OAuth interaction from Phase 2's sign-in. Phase 4 adds the Storage Scanner's API surface: start/list scans (`/v1/connectors/{id}/scans`), status+progress and cancel (`/v1/scans/{id}`, `/v1/scans/{id}/cancel`) — `ScanService` enqueues the actual scan onto `apps/worker`'s queue via a lightweight Celery client (`app/infrastructure/queue/scan_producer.py`) rather than doing any scanning itself; see [`Docs/phases/PHASE_04_STORAGE_INTELLIGENCE.md`](../../Docs/phases/PHASE_04_STORAGE_INTELLIGENCE.md), [ADR-015](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-015-extract-dbsecurityconnector-code-from-appsbackend-into-packagesshared-ahead-of-phase-4) (the `packages/shared` refactor this phase required), and [ADR-016](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-016-storage-scanner-design--two-pass-hierarchy-resolution-cooperative-cancellation-job-level-retry) (the scanner's own design). The DB models, repositories, and Google OAuth client that used to live under `app/infrastructure/` moved to `packages/shared/vault_shared` in this phase so `apps/worker` could use them too — see ADR-015 before adding anything new to either location. 

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Requires `DATABASE_URL`/`REDIS_URL` etc. (see repo-root `.env.example`).

