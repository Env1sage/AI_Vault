# 03 — Architecture Decision Log

Status: **Append-only log.** Every significant technical decision gets an entry here, in order, and entries are never edited to erase history — a reversed decision gets a new ADR that supersedes the old one. See [`00_ENGINEERING_HANDBOOK.md`](00_ENGINEERING_HANDBOOK.md) §30 for when an ADR is required.

Format per entry: Status, Context, Decision, Consequences, Alternatives considered.

---

## ADR-001: Monorepo with pnpm workspaces + Turborepo

**Status:** Accepted

**Context:** `apps/frontend`, `apps/backend`, and `apps/worker` will share types, auth helpers, and the AI Gateway constantly (Handbook §6.1.1, §8.14). Multiple repos would mean either a published internal package registry before Phase 1 starts, or duplicated code drifting out of sync.

**Decision:** Single repository. pnpm workspaces for dependency linking across `apps/*` and `packages/*`; Turborepo for task orchestration/caching (build, lint, test) across the workspace.

**Consequences:** Shared code changes atomically with its consumers in one PR. Repo grows larger over time; CI must scope tasks per-package (Turborepo's affected-package detection) rather than always running everything. Revisit if `apps/*` ever need independent release cadence or separate ownership strong enough to justify a split.

**Alternatives considered:** Polyrepo with a published `@vault/*` npm scope (rejected: package registry + versioning overhead not justified before there's a second consumer team); Nx (comparable to Turborepo; Turborepo chosen for lighter configuration surface at this project's size).

---

## ADR-002: TypeScript on Node.js (LTS) as the sole language/runtime

**Status:** Superseded in part by [ADR-012](#adr-012-revise-phase-1-stack-vite--react-frontend-fastapi--celery-backendworker) — the platform is polyglot from Phase 1 onward (TypeScript for `apps/frontend`, Python for `apps/backend`/`apps/worker`). Kept for historical context; do not use this ADR to justify a TS-only expectation anywhere in the codebase.

**Context:** `packages/types` needs to be consumed without translation by every app. A single language across frontend, backend, and worker means one shared type system, one hiring/skill profile, one toolchain.

**Decision:** TypeScript everywhere, running on the current Node.js LTS release.

**Consequences:** No polyglot flexibility (e.g. no reaching for Python for AI/data-science-style code without a boundary/FFI decision later). Strict `tsconfig` (via `packages/config`) enforced across all apps/packages from Phase 1.

**Alternatives considered:** Python backend + TS frontend (rejected: would require a serialized contract layer instead of shared `packages/types`, reintroducing the drift problem ADR-001 avoids).

---

## ADR-003: Next.js for the frontend

**Status:** Superseded by [ADR-012](#adr-012-revise-phase-1-stack-vite--react-frontend-fastapi--celery-backendworker) — the frontend is Vite + React (SPA), not Next.js.

**Context:** `apps/frontend` (Phase 6, Founder Dashboard) needs server-rendered pages for fast initial load of inventory/recommendation views plus API routes for lightweight BFF needs.

**Decision:** Next.js (React) as the frontend framework.

**Consequences:** Couples the frontend to React's ecosystem and Next's conventions (file-based routing, server components). Well-trodden path for the dashboard-style UI described in Handbook's UI/UX standards.

**Alternatives considered:** Plain Vite + React SPA (rejected: would need a separate solution for SSR/SEO-adjacent concerns the dashboard doesn't strictly need yet, but Next costs little extra at this stage and keeps the option open).

---

## ADR-004: NestJS for the backend API

**Status:** Superseded by [ADR-012](#adr-012-revise-phase-1-stack-vite--react-frontend-fastapi--celery-backendworker) — the backend is FastAPI (Python), not NestJS.

**Context:** `apps/backend` needs enforced layering (Handbook §6.1.2: presentation/application/domain/infrastructure), dependency injection for swappable infrastructure (datastore, AI Gateway, queue producer), and RBAC/guard support from Phase 2 onward.

**Decision:** NestJS as the backend framework.

**Consequences:** Opinionated module/DI structure maps directly onto the layered architecture instead of fighting it. Steeper initial boilerplate than a minimal Express app, accepted as the cost of enforced structure across many future phases and contributors.

**Alternatives considered:** Express + hand-rolled layering (rejected: layering would be convention-only with nothing stopping drift over 8 phases); Fastify (comparable performance profile, less mature DI/module story for this project's layering needs).

---

## ADR-005: Node.js worker on BullMQ, Redis as queue/cache

**Status:** Accepted for the Redis choice; the queue *library* is superseded by [ADR-012](#adr-012-revise-phase-1-stack-vite--react-frontend-fastapi--celery-backendworker) — the worker is Python (Celery), so BullMQ (a Node.js library) does not apply. Redis remains the broker/cache exactly as decided here.

**Context:** Handbook §8.15 requires the worker to be a stateless, horizontally scalable queue consumer with durable job state and retry semantics — needed as soon as Phase 3's scanner has to walk large storage accounts without blocking a request.

**Decision:** BullMQ (Redis-backed) as the job queue; Redis doubles as the cache layer for hot read paths.

**Consequences:** Redis becomes a required piece of local/dev infrastructure from Phase 1's `infrastructure/docker` setup onward. BullMQ's retry/backoff/dead-letter primitives are used directly rather than hand-rolled, keeping worker job-handling logic thin.

**Alternatives considered:** SQS/cloud-managed queue (rejected for local-dev friction pre-deployment-target decision); a Postgres-backed job queue (rejected: would couple job throughput to the primary datastore's write load).

---

## ADR-006: PostgreSQL as the primary datastore

**Status:** Accepted

**Context:** Inventory data (Handbook §8.2), recommendations (§8.6), RBAC/audit data (§13), and relational structures (files ↔ folders ↔ permissions ↔ tenants) all benefit from strong relational integrity and transactional guarantees, plus mature JSON column support for connector-specific metadata that doesn't need its own table.

**Decision:** PostgreSQL as the single primary datastore across phases.

**Consequences:** One datastore to operate, back up, and reason about for consistency. `tenant_id`-scoped schema/row-level patterns (Handbook §13) are enforced via Postgres constraints/RLS where practical, not just application code. A dedicated search/vector store is a separate future ADR if Phase 4/5's similarity search needs outgrow Postgres extensions (e.g. `pgvector`).

**Alternatives considered:** MongoDB (rejected: weaker fit for the relational audit/RBAC/tenant model this system leans on throughout); separate OLTP + document store from day one (rejected as premature — revisit only if a concrete phase requirement demands it).

---

## ADR-007: AI Gateway as an internal provider-agnostic abstraction

**Status:** Accepted

**Context:** Handbook §12 — the LLM must be replaceable without touching `apps/*` business logic. This has to be a real architectural boundary, not a naming convention.

**Decision:** A single module in `packages/shared` (the AI Gateway) is the only code in the repository permitted to import a provider SDK. It exposes capability-based methods (`complete`, `embed`, `classify`, …) with provider selection as an internal routing decision. Each supported provider (Claude, GPT, Gemini, Ollama, Qwen, Mistral) gets a thin adapter behind that interface, implemented as each phase actually needs it — not all six on day one.

**Consequences:** Every call site depends on the Gateway's interface, never a provider type. Adding/removing/swapping a provider touches only the Gateway + its adapter. This is enforced by code review (Handbook §26 review checklist) and can be enforced mechanically later (e.g. a lint rule banning provider-SDK imports outside `packages/shared`) once the tooling exists.

**Alternatives considered:** Direct provider SDK calls per app with a shared "prompt library" (rejected — this is exactly the coupling the AI Philosophy in Handbook §12 exists to prevent); a third-party LLM router service (rejected for now — adds an external dependency/cost before there's a concrete multi-provider requirement; revisit if adapter maintenance burden grows).

---

## ADR-008: Git branching — main / production / develop / feature

**Status:** Accepted

**Context:** Need a branching model that supports the sprint lifecycle in Handbook §4 (phase implemented → manually tested → CTO-reviewed → released) with a clear, always-deployable integration point and an explicit production gate.

**Decision:** Four-tier model as documented in Handbook §24-25: `feature/*` → `develop` (PR + CI + review) → `production` (promoted after manual test + CTO review) → `main` (tagged releases only). No direct pushes to the three long-lived branches.

**Consequences:** Every change is traceable through a PR. An extra promotion step (`develop` → `production` → `main`) versus a simpler two-branch model, accepted because the lifecycle already requires a manual-test gate and a CTO-review gate as distinct steps — the branch structure just makes those gates visible in git history instead of implicit.

**Alternatives considered:** Trunk-based development with feature flags (rejected: the sprint lifecycle's explicit human gates fit a promotion-branch model more directly than flag-gated trunk); GitHub Flow (`main` + `feature/*` only) (rejected: collapses the manual-test and production-release gates into one branch, losing the distinction).

---

## ADR-009: Docker Compose for local/dev infra, GitHub Actions for CI/CD

**Status:** Accepted

**Context:** Phase 1 needs a reproducible local environment (Postgres, Redis, the three apps) and a CI pipeline that can run lint/typecheck/test on every PR per the Git strategy's merge policy (Handbook §24).

**Decision:** Docker + Docker Compose for local development infra (`infrastructure/docker`). GitHub Actions for CI/CD (`.github/workflows`), since the repo is already GitHub-hosted and Actions needs no separate CI system to operate.

**Consequences:** Deployment target (the orchestrator production actually runs on — Kubernetes, ECS, a PaaS, etc.) remains an open decision, deliberately deferred to a later ADR once Phase 1/8 requirements make the tradeoffs concrete rather than guessed at now.

**Alternatives considered:** None seriously considered for local dev (Compose is the standard fit for a multi-service TS monorepo); CircleCI/Jenkins for CI (rejected: adds an external system with no advantage over Actions given GitHub hosting).

---

## ADR-010: Caveman Repository workflow as standard operating discipline

**Status:** Accepted

**Context:** Handbook §29. As the repo grows across 8 phases, "load the whole repo into context for every task" stops scaling — for a human skimming files or an AI agent implementing a phase.

**Decision:** Standardize on loading only the modules a task's phase document identifies as affected, using this handbook + the relevant phase doc + targeted search as the primary navigation aids, documented as a workflow discipline rather than tied to any specific tool.

**Consequences:** Makes the strict module boundaries in Handbook §5-6.1 load-bearing, not just tidy — they're what makes "only the affected modules" a well-defined, small set in the first place. Tool-agnostic, so it survives a change of IDE/agent/editor.

**Alternatives considered:** Full-repository context loading per task (rejected — doesn't scale past a couple of phases, and makes diffs harder to keep scoped per the PR review checklist).

---

## ADR-011: Expand platform architecture from storage cleanup to a full knowledge-brain pipeline

**Status:** Accepted

**Context:** The original Engineering Handbook scoped System Architecture around ten subsections (§5.1-5.10 in the pre-revision numbering) sufficient to describe scan → recommend → execute for storage hygiene. The product vision (Handbook §1, Project Master §1-2) is broader: an "AI Employee" that understands, organizes, learns, connects, recommends, executes, and protects an organization's knowledge — storage cleanup is the first slice, not the ceiling. The handbook needed to name the additional pipeline stages (Metadata Engine, Knowledge Builder, Embedding Engine, Search Engine, Notification Engine, Audit Engine) and platform-facing modules (Founder Dashboard, Employee Dashboard, Authentication) explicitly, so later phases have module contracts to implement against instead of inventing them ad hoc mid-phase.

**Decision:** Expand the Core Platform Modules section (Handbook §8) to fifteen modules with explicit Purpose/Responsibilities/Inputs/Outputs/Dependencies/Future Expansion contracts; add Database Philosophy (§9), AI Intelligence Pipeline (§10), Founder/Employee Journeys (§14-15), Department Intelligence (§16), a Recommendation Engine deep dive (§17), and Future Connector Architecture (§18) as dedicated sections. No existing architectural decision (technology stack, AI Gateway abstraction, layering, event-driven processing, Git strategy) was changed — this is additive scope on top of ADR-001 through ADR-010, not a replacement of any of them. All existing handbook section numbers shifted to accommodate the new material; every cross-reference to a handbook section elsewhere in `Docs/` was updated in the same pass.

**Consequences:** Phases 3-7 now have named modules to implement against (e.g. Phase 4 "Storage Intelligence" maps onto the Metadata Engine + Knowledge Builder contracts, §8.3-8.4) rather than being scoped from a vaguer "storage intelligence" description. Department Intelligence (§16) is explicitly profile-based, not per-department AI agents — a constraint future phases must not violate without a new ADR. Section-number churn is a one-time cost, absorbed in this revision; future handbook edits should prefer appending subsections over renumbering where practical, to avoid repeating this cross-reference maintenance.

**Alternatives considered:** Leaving the new modules undocumented until their phase is scoped (rejected — the phase docs for 4-7 already reference the modules by name in their Objective sections, e.g. Phase 4/5's dependency on scanner/recommendation-engine concepts, and Documentation Standards §27 requires a phase's Architecture section to fit the system architecture, which requires the architecture to already describe the module); a separate "Platform Modules" document outside the handbook (rejected — Handbook §2 states it is *the* single source of truth for how the system is built, and splitting module contracts out would fragment that).

---

## ADR-012: Revise Phase 1 stack — Vite + React frontend, FastAPI + Celery backend/worker

**Status:** Accepted

**Context:** [`PHASE_01_FOUNDATION.md`](phases/PHASE_01_FOUNDATION.md) (CTO-authored, founder-approved) specifies a different implementation stack than ADR-002/003/004/005 had converged on: React 19 + Vite (not Next.js) for `apps/frontend`; FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2 (not NestJS) for `apps/backend`; Celery (not BullMQ) for `apps/worker`. The founder confirmed, when asked directly at the start of Phase 1 implementation, that the Phase 1 document's stack is authoritative over the Handbook's — the Handbook was stale on this point, not the phase doc. Per Handbook §30, an ADR must record this before the code lands, not after.

**Decision:** Adopt a **polyglot monorepo**: TypeScript for `apps/frontend` and the frontend-facing packages (`packages/types`, `packages/ui`, the TS half of `packages/config`); Python (3.13, current stable) for `apps/backend` and `apps/worker`, sharing a Python package under `packages/shared` for cross-cutting concerns (structured logging, typed errors, config loading) instead of a TS one. Concretely:
- Frontend: Vite + React 19 + TypeScript + Tailwind CSS v4 + TanStack Router/Query + Zustand + React Hook Form + Zod + shadcn/ui. Next.js (ADR-003) is dropped — no SSR requirement has materialized and a SPA is simpler to operate for a dashboard-style app.
- Backend: FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2, still organized into the Handbook §6.1.2 presentation/application/domain/infrastructure layers — that layering is framework-agnostic and holds under FastAPI exactly as it would under NestJS. NestJS (ADR-004) is dropped.
- Worker: Celery, still consuming Redis (ADR-005's Redis decision is retained in full — only the Node.js BullMQ library is dropped in favor of Celery, Python's equivalent).
- pnpm workspaces + Turborepo (ADR-001) are retained, but scoped to the TypeScript portion of the tree (`apps/frontend` + TS `packages/*`) since Python has no place in a pnpm workspace. The Python apps (`apps/backend`, `apps/worker`, `packages/shared`) are each independent Python projects (`pyproject.toml`), with `packages/shared` installed into the other two as an editable local dependency.

**Consequences:** `packages/types`'s original promise — "one shared type system, zero translation layer" (ADR-002) — no longer holds across the whole stack: Python (Pydantic) and TypeScript can't share a type definition directly. API contracts must be kept in sync manually in Phase 1, with FastAPI's auto-generated OpenAPI schema as the source of truth; generating TS types from that OpenAPI schema (e.g. `openapi-typescript`) is flagged as follow-up tooling work for an early future phase, not solved now. `packages/shared` is no longer TypeScript — anything under it must be Python, and any future TS cross-cutting code shared only among frontend-adjacent TS packages belongs in `packages/config` or a new TS-specific package, not here. CI (§11, §21) now needs two independent toolchains (Node + Python) rather than one, which is reflected in `.github/workflows/ci.yml`'s job matrix.

**Alternatives considered:** Keep the original TS-everywhere stack and treat the Phase 1 document as the one that's wrong (rejected — the founder explicitly confirmed the Phase 1 document is authoritative for this decision when the conflict was surfaced); rewrite `packages/types` as a codegen target from day one (deferred, not rejected outright — reasonable future work once the backend's OpenAPI surface is non-trivial, but premature for a Phase 1 that has no business endpoints yet).

---

