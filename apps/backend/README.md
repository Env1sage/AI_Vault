# apps/backend

API and application-service layer for AI Project Vault. Owns request handling, orchestration, RBAC enforcement, and the AI Gateway boundary.

Never calls an LLM provider SDK directly — all model calls route through `packages/shared`'s AI Gateway abstraction (built in Phase 6 — see [ADR-018](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-018-ai-intelligence-engine-phase-6--ai-gateway-abstraction-local-first-embeddings-mean-centered-similarity-and-a-stubbed-completion-provider)). Never talks to `apps/worker`'s internals directly; communicates only via the documented queue contracts.

FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2 (ADR-012 — not NestJS), layered per Engineering Handbook §6.1.2 (`app/presentation`, `app/application`, `app/domain`, `app/infrastructure`). Phase 1 shipped only `/health/live`, `/health/ready`, `/v1/version` — no business logic. Phase 2 added the Identity domain: Google Identity Services login (`/v1/auth/login`), JWT + rotating-refresh-cookie sessions (`/v1/auth/refresh`, `/v1/auth/logout`), RBAC (`/v1/users/me`, `/v1/organizations/current`) — see [`Docs/phases/PHASE_02_AUTH.md`](../../Docs/phases/PHASE_02_AUTH.md) and [ADR-013](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-013-phase-2-session-strategy--client-side-google-identity-services-short-lived-jwt--rotating-httponly-refresh-cookie). 

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Requires `DATABASE_URL`/`REDIS_URL` etc. (see repo-root `.env.example`).

