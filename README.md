# AI Project Vault

An intelligence layer over an organization's storage (starting with Google Workspace): it scans, understands, recommends, and — with explicit approval — acts on what it finds. The LLM is an interchangeable component behind an AI Gateway, not the product itself.

This repository has completed **Phase 10 — Production Hardening, Enterprise Readiness & V1 Release**, the last of ten planned phases: the monorepo, backend, worker, frontend, database, queue, Docker Compose, CI, authentication (Google sign-in, JWT sessions, RBAC), organization management, a provider-agnostic storage-connector platform (Google Workspace OAuth, encrypted token storage, automatic refresh), a read-only storage scanner (provider-agnostic traversal, `Folder`/`File` inventory, full + incremental sync, worker-queue execution, cancellation), a deterministic Knowledge Engine (content extraction, classification, knowledge attributes, relationship discovery, auto-triggered after every scan), an AI Gateway-backed intelligence layer (free/offline local embeddings, hybrid metadata+semantic search, RAG-style context assembly with citations, conversational querying, auto-triggered after every enrichment), an organization-scoped Recommendation Engine (11 deterministic rules across storage/knowledge/security/collaboration/productivity, explainable prioritization, a Founder Command Center dashboard with historical trend data, auto-triggered after every embedding run), an Execution Engine & Human Approval System (deterministic execution plans built from 3 of those 11 rules, an approval workflow gating every mutating action on explicit human sign-off, permission validation, move/rename/archive/remove-duplicate/update-metadata execution workers with no permanent deletion, verification, rollback via Google Drive's own Trash, and immutable execution audit logging), an Automation Engine & Workflow Platform (a node-graph Workflow Builder with draft/published/history versioning, scheduled/event/manual triggers driven by a DB-polled scheduler, a versioned Policy Engine where a published policy can auto-execute an `EXECUTE_ACTION` node as a second, fully-audited kind of approver without ever bypassing the Approval System, full pause/resume/cancel execution resumability, an in-app + stubbed-email Notification Framework, and 6 starter automation templates), and a production-hardening pass (response security headers, expanded rate limiting, Prometheus/OpenTelemetry/Sentry observability — the latter two off until configured, matching the LLM/email stub pattern — structured-log correlation IDs spanning both apps, a real drilled backup/restore procedure, and a validated Terraform reference implementation for AWS) all exist. The AI Gateway's completion side is still stubbed to a deterministic, never-invents-an-answer fallback — no real LLM provider is wired in yet, and the email notification channel is likewise stubbed to logging only — no real email is sent. Nothing in this platform ever mutates connected storage without an owner or admin's explicit, individually-recorded approval (a policy's auto-execution is itself owner/admin-configured, versioned, and audited exactly like a manual decision); the founder must reconnect Google Workspace with write access before any real execution can run. See [`Docs/`](Docs/) for the full governing documentation before writing or reviewing any code — start with [`Docs/04_DEPLOYMENT_HANDBOOK.md`](Docs/04_DEPLOYMENT_HANDBOOK.md) if you're deploying this, or [`Docs/14_USER_GUIDE.md`](Docs/14_USER_GUIDE.md) if you're using it.

## Running it locally

```bash
./infrastructure/scripts/bootstrap.sh                              # one-time setup
docker compose -f infrastructure/docker/docker-compose.yml up       # full stack
```

Frontend: http://localhost:5173 (`/login`, `/dashboard`, `/profile`, `/organization`, `/storage-connections`, `/scans`, `/files`, `/files/$fileId`, `/search`, `/chat`, `/chat/$conversationId`, `/recommendations`, `/recommendations/$recommendationId`, `/execution-plans`, `/execution-plans/$executionPlanId`, `/approvals`, `/execution-jobs`, `/execution-jobs/$executionJobId`, `/workflows`, `/workflows/$workflowId`, `/workflows/$workflowId/builder`, `/workflow-executions`, `/workflow-executions/$workflowExecutionId`, `/workflow-policies`, `/automation-templates`, `/notifications`, `/automation`) · Backend: http://localhost:8000 (`/health/live`, `/health/ready`, `/v1/version`, `/v1/docs`, `/v1/auth/*`, `/v1/users/me`, `/v1/organizations/current`, `/v1/connectors/*`, `/v1/connectors/{id}/scans`, `/v1/scans/*`, `/v1/connectors/{id}/files`, `/v1/files/*`, `/v1/connectors/{id}/enrichment`, `/v1/enrichment/*`, `/v1/search`, `/v1/conversations/*`, `/v1/connectors/{id}/embedding`, `/v1/embedding/*`, `/v1/dashboard`, `/v1/recommendations/*`, `/v1/execution-plans/*`, `/v1/approvals/*`, `/v1/execution-jobs/*`, `/v1/workflows/*`, `/v1/workflow-executions/*`, `/v1/workflow-policies/*`, `/v1/notifications`, `/v1/automation-templates/*`).

Google sign-in requires a real OAuth Client ID (Google Cloud Console → APIs & Services → Credentials): set `GOOGLE_CLIENT_ID` in the root `.env` and `VITE_GOOGLE_CLIENT_ID` in `apps/frontend/.env` to the same value (see [ADR-013](Docs/03_ARCHITECTURE_DECISIONS.md#adr-013-phase-2-session-strategy--client-side-google-identity-services-short-lived-jwt--rotating-httponly-refresh-cookie)). Connecting Google Workspace storage is a **separate** OAuth flow (see [ADR-014](Docs/03_ARCHITECTURE_DECISIONS.md#adr-014-phase-3-google-workspace-connector--server-side-authorization-code-flow-with-a-frontend-hosted-callback-encrypted-token-storage)) — add `GOOGLE_WORKSPACE_REDIRECT_URI` as an authorized redirect URI on that same OAuth client, and set `CONNECTOR_ENCRYPTION_KEY` (a Fernet key — a local-dev-only one is already in `.env.example`, regenerate for anything else).

Stack per [ADR-012](Docs/03_ARCHITECTURE_DECISIONS.md#adr-012-revise-phase-1-stack-vite--react-frontend-fastapi--celery-backendworker): Vite + React + TypeScript frontend, FastAPI + Celery (Python) backend/worker, PostgreSQL + Redis.

## Start here

| Document | Purpose |
|---|---|
| [`Docs/00_ENGINEERING_HANDBOOK.md`](Docs/00_ENGINEERING_HANDBOOK.md) | Architecture, tech stack, security, Git workflow, coding standards — the rules every phase must follow. |
| [`Docs/01_PROJECT_MASTER.md`](Docs/01_PROJECT_MASTER.md) | Vision, roles, phase roadmap, success criteria. |
| [`Docs/02_CTO_DASHBOARD.md`](Docs/02_CTO_DASHBOARD.md) | Live executive status: sprint, progress, risks, blockers. Updated every sprint. |
| [`Docs/03_ARCHITECTURE_DECISIONS.md`](Docs/03_ARCHITECTURE_DECISIONS.md) | ADR log — every significant technical decision and why it was made. |
| [`Docs/04_DEPLOYMENT_HANDBOOK.md`](Docs/04_DEPLOYMENT_HANDBOOK.md) | Environments, Terraform, CI/CD deploy pipeline, rollback. |
| [`Docs/05_API_DOCUMENTATION.md`](Docs/05_API_DOCUMENTATION.md) | REST API conventions and the full endpoint index. |
| [`Docs/06_ARCHITECTURE_DOCUMENTATION.md`](Docs/06_ARCHITECTURE_DOCUMENTATION.md) | System diagram, layer boundaries, cross-cutting concerns. |
| [`Docs/07_DATABASE_DOCUMENTATION.md`](Docs/07_DATABASE_DOCUMENTATION.md) | Schema, relationships, migration history. |
| [`Docs/08_SECURITY_GUIDE.md`](Docs/08_SECURITY_GUIDE.md) | Auth, encryption, rate limiting, threat model. |
| [`Docs/09_OPERATIONS_RUNBOOK.md`](Docs/09_OPERATIONS_RUNBOOK.md) | What to check and do when something's wrong in production. |
| [`Docs/10_DISASTER_RECOVERY_GUIDE.md`](Docs/10_DISASTER_RECOVERY_GUIDE.md) | Backup/restore procedure and recovery targets. |
| [`Docs/11_MONITORING_GUIDE.md`](Docs/11_MONITORING_GUIDE.md) | Metrics, dashboards, correlation IDs. |
| [`Docs/12_CONTRIBUTOR_GUIDE.md`](Docs/12_CONTRIBUTOR_GUIDE.md) | Fast-start setup and how to land a change. |
| [`Docs/13_RELEASE_NOTES.md`](Docs/13_RELEASE_NOTES.md) | What's in Version 1.0. |
| [`Docs/14_USER_GUIDE.md`](Docs/14_USER_GUIDE.md) | How to actually use the product (non-developer audience). |
| [`Docs/15_COMPLIANCE_READINESS.md`](Docs/15_COMPLIANCE_READINESS.md) | GDPR/SOC 2/ISO 27001 readiness notes. |
| [`Docs/phases/`](Docs/phases/) | One document per implementation phase (objective, architecture, DoD). |

## Repository layout

```text
apps/            deployable services (frontend, backend, worker)
packages/        shared code consumed by apps/ (shared, types, ui, config)
Docs/            engineering documentation and phase specs
infrastructure/  docker, terraform (AWS reference IaC), monitoring configs, scripts
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
