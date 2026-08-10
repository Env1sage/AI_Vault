# Phase 1 — Completion Report

**Phase:** [`PHASE_01_FOUNDATION.md`](PHASE_01_FOUNDATION.md) — Engineering Foundation & Infrastructure
**Status:** Implemented by Claude. Awaiting founder manual test and CTO review (Engineering Handbook §4 lifecycle) before being marked complete in [`01_PROJECT_MASTER.md`](../01_PROJECT_MASTER.md).
**Date:** 2026-07-28

---

## 1. Stack decision (read this first)

Before writing code, a real conflict surfaced: the Engineering Handbook and ADR-002/003/004/005 specified a TypeScript-everywhere stack (NestJS, Next.js, BullMQ), while `PHASE_01_FOUNDATION.md` itself specifies Python/FastAPI/Celery + Vite/React. Asked directly, the founder confirmed the Phase 1 document is authoritative. This is now recorded as **[ADR-012](../03_ARCHITECTURE_DECISIONS.md#adr-012-revise-phase-1-stack-vite--react-frontend-fastapi--celery-backendworker)**, with ADR-002/003/004/005 marked superseded (in part) rather than edited away, per the Handbook's append-only ADR convention. The result is a deliberately **polyglot monorepo**:

- `apps/frontend` + `packages/types`/`packages/ui`/`packages/config` (TS half) → pnpm workspace + Turborepo.
- `apps/backend` + `apps/worker` + `packages/shared` (Python half) → independent `pyproject.toml`/`requirements.txt` projects, `packages/shared` installed into the other two as an editable path dependency.

## 2. Repository changes

```text
apps/backend/          FastAPI app — presentation/application/domain/infrastructure layers
  app/main.py             app factory: CORS, request-context middleware, error handlers, routers
  app/presentation/       health_router (/health/live, /health/ready), v1_router (/v1/version)
  app/infrastructure/     SQLAlchemy engine/session (db/), Redis client (cache/)
  app/domain/, application/  empty placeholders — first real code lands Phase 2
  alembic/                env.py sources DATABASE_URL from vault_shared.get_settings(); one migration
                          (0001_enable_pgcrypto) — no business tables yet, per phase scope
  requirements.txt, requirements-dev.txt, pyproject.toml (ruff config)

apps/worker/            Celery app — broker/backend on Redis
  worker/celery_app.py     task_acks_late + task_reject_on_worker_lost (no lost job state, Handbook §8.15)
  worker/tasks/health.py   worker.health.ping — proves the queue round-trip; no business jobs yet

apps/frontend/          Vite + React 19 + TypeScript SPA
  src/routes/              TanStack Router file-based routes (__root.tsx, index.tsx — connectivity widget)
  src/components/          ErrorBoundary, LoadingScreen, ui/Button (shadcn convention)
  src/lib/                 api-client.ts (typed fetch wrapper + ApiError), query-client.ts, utils.ts (cn())
  components.json          shadcn/ui CLI config, ready for `npx shadcn add <component>` in later phases

packages/shared/        Python — vault_shared: Settings (pydantic-settings), JSON structured logging
                        with request-ID propagation, typed error hierarchy (VaultError + 5 subclasses)
packages/types/         TS — API contract types mirroring the backend's health/version/error responses
packages/config/        Split by language: typescript/ (tsconfig base, eslint flat config),
                        python/ (ruff.toml, mypy.ini) — every app extends these, none duplicate rules

tests/unit/{backend,worker,shared}/   23 + 18 tests (some shared) — mocked dependencies
tests/integration/backend/           readiness against a real Postgres/Redis — skips if unreachable
tests/e2e/                            full-stack HTTP checks — skips if the stack isn't running

infrastructure/docker/   backend/worker/frontend Dockerfiles + docker-compose.yml (Postgres, Redis,
                        backend, worker, frontend)
infrastructure/scripts/  bootstrap.sh (one-command setup), migrate.sh (alembic upgrade head)

.github/workflows/ci.yml   frontend / backend / worker / docker-build jobs, all wired to run on every PR
```

## 3. Docker / infrastructure

- **Dockerfiles build with the repo root as context** (not `infrastructure/docker/`) so `packages/shared` can sit alongside `apps/backend`/`apps/worker` inside the image at the same relative path their `requirements.txt` expects (`-e ../../packages/shared`).
- **Non-obvious bug caught and fixed during implementation:** pip resolves a `-e <relative-path>` line in a requirements file relative to the **process's current working directory**, not the requirements file's own location. This broke the first draft of both Dockerfiles and `bootstrap.sh` (they ran `pip install` from the repo root). Fixed by `cd`/`WORKDIR`-ing into `apps/backend`/`apps/worker` immediately before the install step in all three places. Verified by simulating the exact directory layout locally (outside Docker, since no daemon was available — see §6) and confirming `vault_shared` imports correctly afterward.
- `docker-compose.yml`: `postgres` (16-alpine), `redis` (7-alpine), `backend` (uvicorn `--reload`, bind-mounted source), `worker` (Celery, bind-mounted source), `frontend` (Vite dev server, `target: development`, anonymous volume over `node_modules` so the bind mount doesn't shadow installed deps). Healthchecks on all four; `depends_on: condition: service_healthy` gates backend/worker startup on Postgres+Redis being ready.
- `frontend.Dockerfile` also has unused-yet `build`/`production` (nginx-served static) stages for the Phase 8 release-hardening pass.

## 4. Environment variables

Documented in `.env.example` (repo root, consumed by `vault_shared.settings.Settings`) and `apps/frontend/.env.example` (Vite only reads `VITE_`-prefixed vars, so it's separate): `SERVICE_NAME`, `ENVIRONMENT`, `LOG_LEVEL`, `DATABASE_URL`, `REDIS_URL`, `CORS_ALLOW_ORIGINS`, `JWT_SECRET`/`AI_GATEWAY_KEY`/`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` (placeholders only — Phase 2/5 features), `VITE_API_BASE_URL`.

## 5. CI (`.github/workflows/ci.yml`)

Four jobs on every PR into `develop`/`main` and every push to `develop`: **frontend** (pnpm install, lint, typecheck, vitest, vite build), **backend** (ruff, mypy, `alembic upgrade head` against a real Postgres service container, pytest unit+integration), **worker** (ruff, mypy, pytest unit), **docker-build** (builds all three Dockerfiles, `push: false`, catching Dockerfile regressions on every PR). `e2e.yml` and the two deploy workflows remain intentionally unimplemented — no critical-path flow exists yet to drive end-to-end, and the deploy target is still an open ADR-009 question.

## 6. Tests and what was actually verified in this environment

Docker Desktop on this machine's macOS version is too old for the installed Docker Desktop build, and no `dockerd` is reachable — **`docker compose up` itself was not run here.** Everything short of that was:

- Backend: 23 unit tests (health live/ready — mocked healthy, DB-down, Redis-down cases; version; typed-error → HTTP shape mapping; unexpected-exception → generic 500) + `ruff`/`mypy` clean. Alembic verified via `alembic upgrade head --sql` (offline mode) — generates the exact expected `CREATE EXTENSION` SQL without needing a live database.
- Worker: 18 unit tests (`ping` task registered and runs eagerly, at-least-once delivery config asserted) + `ruff`/`mypy` clean.
- Frontend: 10 vitest tests (`cn()`, `ApiError`/api-client success+failure+non-JSON-body paths, ErrorBoundary catches a throwing child, LoadingScreen renders) + eslint/tsc clean + `vite build` succeeds.
- **Live integration, not just mocks:** ran the backend (`uvicorn`) and frontend (`vite dev`) as real local processes side by side and hit them with `curl` — confirmed `/health/live`, `/health/ready` (correctly reports `degraded` with no Postgres/Redis present), `/v1/version`, and that a request with `Origin: http://localhost:5173` gets back the correct `access-control-allow-origin` header (CORS is scoped to the configured frontend origin, not wildcarded).
- `docker compose config` (schema resolution, not a build) validated `docker-compose.yml` cleanly.
- Root Turborepo tasks (`pnpm run lint|typecheck|test|build`) all pass across `@vault/frontend`, `@vault/types`, `@vault/config`.

**This is the concrete gap for the founder's manual-test step:** run `docker compose -f infrastructure/docker/docker-compose.yml up` for real and confirm all four services report healthy, matching the Manual QA Checklist in `PHASE_01_FOUNDATION.md`.

## 7. Known limitations / follow-ups

- `packages/types` is no longer a zero-translation shared type layer across the whole stack (ADR-012 consequence) — kept in sync by hand against the backend's OpenAPI schema for now. Generating it via `openapi-typescript` is flagged as future tooling work, not solved in Phase 1.
- The `01_PROJECT_MASTER.md` roadmap table and `Docs/phases/PHASE_0N_*.md` filenames still reflect the original 8-phase plan; the actual content of `PHASE_02`–`PHASE_08` describes a renumbered 10-phase plan, and `PHASE_09.md`/`PHASE_10.md` are empty placeholders. Left unreconciled per explicit founder instruction (phases are being executed one at a time from individual prompts).
- No live Postgres/Redis available in this implementation environment (see §6) — CI's service containers are the first real live-database check this code will get; the founder's `docker compose up` is the second and more important one.

## 8. Recommendation for Phase 2

The Identity & Organization Platform (per `Docs/phases/PHASE_02_AUTH.md`) can build directly on this foundation: `app/domain`/`app/application` are empty and ready for the first real entities, Alembic has one migration to build on top of (`pgcrypto` is enabled for UUID PKs), and the frontend's route tree/API client/error handling are all in place for a login flow to slot into.
