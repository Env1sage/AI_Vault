# AI Project Vault

An intelligence layer over an organization's storage (starting with Google Workspace): it scans, understands, recommends, and — with explicit approval — acts on what it finds. The LLM is an interchangeable component behind an AI Gateway, not the product itself.

This repository currently has **Phase 1 — Foundation** in place: the monorepo, backend/frontend/worker app skeletons, Docker Compose local stack, and CI. See [`Docs/`](Docs/) for the full governing documentation before writing or reviewing any code.

## Running it locally

```bash
./infrastructure/scripts/bootstrap.sh                              # one-time setup
docker compose -f infrastructure/docker/docker-compose.yml up       # full stack
```

Stack per [ADR-012](Docs/03_ARCHITECTURE_DECISIONS.md#adr-012-revise-phase-1-stack-vite--react-frontend-fastapi--celery-backendworker): Vite + React + TypeScript frontend, FastAPI + Celery (Python) backend/worker, PostgreSQL + Redis.

## Start here

| Document | Purpose |
|---|---|
| [`Docs/00_ENGINEERING_HANDBOOK.md`](Docs/00_ENGINEERING_HANDBOOK.md) | Architecture, tech stack, security, Git workflow, coding standards — the rules every phase must follow. |
| [`Docs/01_PROJECT_MASTER.md`](Docs/01_PROJECT_MASTER.md) | Vision, roles, phase roadmap, success criteria. |
| [`Docs/02_CTO_DASHBOARD.md`](Docs/02_CTO_DASHBOARD.md) | Live executive status: sprint, progress, risks, blockers. Updated every sprint. |
| [`Docs/03_ARCHITECTURE_DECISIONS.md`](Docs/03_ARCHITECTURE_DECISIONS.md) | ADR log — every significant technical decision and why it was made. |
| [`Docs/phases/`](Docs/phases/) | One document per implementation phase (objective, architecture, DoD). |

## Repository layout

```text
apps/            deployable services (frontend, backend, worker)
packages/        shared code consumed by apps/ (shared, types, ui, config)
Docs/            engineering documentation and phase specs
infrastructure/  docker, deployment and operational scripts
.github/         CI/CD workflows, PR template
tests/           unit, integration, e2e
tools/           internal developer tooling
```

Full rationale for this layout is in the Engineering Handbook's Repository Organization section.

## Working on this repo

1. Read the Engineering Handbook before touching code.
2. Find your task's phase document in `Docs/phases/`.
3. Follow the Git strategy and branch naming convention in the handbook.
4. Every PR uses the template in `.github/PULL_REQUEST_TEMPLATE.md` and must satisfy the phase's Definition of Done.
