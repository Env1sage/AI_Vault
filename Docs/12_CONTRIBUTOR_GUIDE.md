# 12 — Contributor Guide

Status: **Living document**, introduced in Phase 10. Practical "how to get set up and land a change" guide. For architectural rules and coding standards in depth, see the [Engineering Handbook](00_ENGINEERING_HANDBOOK.md) §24-25 (Git strategy, branch naming) and throughout. This document is the fast-start version.

---

## 1. Setup

```bash
git clone <repo>
cd AI_Vault
infrastructure/scripts/bootstrap.sh     # installs JS deps, creates both Python venvs
cp .env.example .env                     # review before running docker compose
docker compose -f infrastructure/docker/docker-compose.yml up
```

Frontend: http://localhost:5173. Backend: http://localhost:8000/v1/docs. Google sign-in and Workspace connection both need real OAuth credentials — see the root [README](../README.md) for exactly which env vars.

## 2. Repository layout

```text
apps/            deployable services (frontend, backend, worker)
packages/        shared code — shared (Python, both backend+worker), types (TS), ui, config
Docs/            this documentation set
infrastructure/  docker, terraform, monitoring configs, scripts
.github/         CI workflows
tests/           unit, integration, e2e — organized by app, not co-located with source
tools/           internal developer tooling
```

Full rationale in the Handbook's Repository Organization section.

## 3. Making a change

1. Branch off `develop` (Handbook §25 — branch naming convention: `<type>/<short-description>`, e.g. `fix/dashboard-cache-key`).
2. Make the change. Prefer editing existing files; match the surrounding code's style exactly (comments explain *why*, not *what* — see the Handbook's own comment philosophy).
3. Run the relevant checks locally before opening a PR (§4).
4. Open a PR against `develop`, using `.github/PULL_REQUEST_TEMPLATE.md`. CI (lint, typecheck, tests, security scan, Docker build+scan) must be green.
5. If the change touches architecture (a new cross-cutting pattern, a new external dependency, a reversed prior decision), add an ADR to `Docs/03_ARCHITECTURE_DECISIONS.md` in the same PR — decisions are documented where they're made, not retroactively.

## 4. Running checks locally

```bash
# Frontend (from repo root — Turborepo runs all three packages)
pnpm run lint && pnpm run typecheck && pnpm run test && pnpm run build

# Backend
cd apps/backend && source .venv/bin/activate
ruff check ../../apps/backend
mypy --config-file ../../packages/config/python/mypy.ini app alembic
pytest ../../tests/unit/backend ../../tests/unit/shared ../../tests/integration/backend -q

# Worker (same shape)
cd apps/worker && source .venv/bin/activate
ruff check ../../apps/worker
mypy --config-file ../../packages/config/python/mypy.ini worker
pytest ../../tests/unit/worker ../../tests/unit/shared ../../tests/integration/worker -q

# packages/shared — check it directly too, not just through an app's path
# (ADR-021/ADR-022: this has caught real mypy gaps invisible from either app's own check)
cd packages/shared && python -m mypy --config-file ../config/python/mypy.ini vault_shared
```

Integration tests need real Postgres + Redis running (`docker compose up postgres redis`, or your own local instances) — they exercise real database round-trips, not mocks, per this project's established convention (see the "verify job effects, not counters" lesson referenced throughout the ADR log).

## 5. Coding standards (summary — Handbook has the full version)

- Layered architecture per app: presentation → application → domain → infrastructure. Business logic never lives in a route handler or a Celery task function directly — both are thin entry points that call an application service.
- Typed everywhere: Pydantic models for every API request/response, SQLAlchemy 2's typed ORM, mypy strict mode, TypeScript strict mode.
- No comments explaining *what* code does — only *why*, when the why is genuinely non-obvious (a hidden constraint, a workaround, a subtle invariant).
- Errors are typed `vault_shared` exceptions (`NotFoundError`, `ForbiddenError`, etc.) raised from services; only `app/core/error_handlers.py` translates them into HTTP responses.
- Every new cross-cutting capability that both `apps/backend` and `apps/worker` need goes in `packages/shared`, not duplicated — this has happened three times now (the DB layer in ADR-015, execution/approval services in ADR-021, observability in ADR-022) and is a recurring, expected pattern, not an exception.

## 6. Testing conventions

- Unit tests mock external boundaries (DB, Redis, external APIs) but never the code under test itself.
- Integration tests run against real Postgres/Redis — this project's tests have caught real bugs (a wrong CHECK constraint, a missing status transition, a JSONB double-encoding bug) specifically because they asserted actual persisted state, not just "did the job eventually finish." Follow that pattern: assert on what's really in the database after an operation, not just that no exception was raised.
- Worker tests never import from `apps/backend` (and vice versa) — provision test fixtures directly against `packages/shared`'s repositories, matching the same layering the production code itself respects.

## 7. Where things are documented

| Question | Document |
|---|---|
| Why was X built this way? | [ADR log](03_ARCHITECTURE_DECISIONS.md) |
| What does this endpoint do? | [API Documentation](05_API_DOCUMENTATION.md) + live `/v1/docs` |
| How is the system structured? | [Architecture Documentation](06_ARCHITECTURE_DOCUMENTATION.md) |
| What's the current project status? | [CTO Dashboard](02_CTO_DASHBOARD.md) |
| How do I deploy this? | [Deployment Handbook](04_DEPLOYMENT_HANDBOOK.md) |
| Something's broken in production | [Operations Runbook](09_OPERATIONS_RUNBOOK.md) |

## 8. Getting help

This project follows a fixed lifecycle (Handbook §4) — a CTO role authors phase specs, an implementation pass builds each phase fully, a founder does manual QA. If you're contributing outside that lifecycle (a bug fix, a small improvement), open a PR as normal; if you're proposing a new capability, check whether it fits an already-planned phase first (`Docs/phases/`) before building it unprompted.
