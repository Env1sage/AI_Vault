# 01 — Project Master

Status: **Living document.** Owned by the CTO role; updated whenever vision, scope, or roadmap shifts. For *how* we build, see the [Engineering Handbook](00_ENGINEERING_HANDBOOK.md). This document is *what* and *why*.

---

## 1. Vision

AI Project Vault turns an organization's storage — starting with Google Workspace — from a passive pile of files into an actively understood, continuously maintained asset. It scans what exists, understands it with AI-driven analysis, recommends concrete actions (organize, deduplicate, archive, flag stale/sensitive content), and — only with explicit human approval — executes them.

## 2. Product principles

- **The LLM is not the product.** The intelligence pipeline (scan → understand → recommend → execute, with audit at every step) is the product. Models behind the AI Gateway are replaceable parts. See Engineering Handbook §12.
- **Read by default, write by permission.** Every component can observe storage; only the execution engine can change it, and only after explicit approval. See Engineering Handbook §8.6-8.7, §13.
- **Storage-source agnostic by design.** Google Workspace is the first connector, not the only one the architecture assumes. See Engineering Handbook §8.1, §18.
- **Boring, auditable infrastructure.** Every mutating action is logged before and after. Nothing destructive happens silently.

## 3. Roles

See Engineering Handbook §3 for the authoritative definition. Summary: ChatGPT (CTO/architecture/review), Claude (implementation), Founder (approval/QA). No overlap.

## 4. Roadmap

Each phase has its own document under [`Docs/phases/`](phases/) per the Documentation Standards in the handbook (§27). This table is the index and current status; the phase document is the source of truth for scope.

| Phase | Document | Objective | Status |
|---|---|---|---|
| 0 | (this handbook set) | Engineering blueprint — repo structure, standards, no business logic | ✅ Complete |
| 1 | [`PHASE_01_FOUNDATION.md`](phases/PHASE_01_FOUNDATION.md) ([report](phases/PHASE_01_COMPLETION_REPORT.md)) | Bootstrap apps/backend, apps/frontend, apps/worker skeletons; base infra (DB, queue, Docker Compose); CI | 🟡 Implemented — awaiting founder manual test & CTO review |

Phase order reflects dependency, not just priority — e.g. Phase 5's recommendation engine needs Phase 4's intelligence signals and Phase 3's inventory to have something to reason about. Phase 10 is the exception to "dependency" — it hardens every prior phase's product code rather than adding new product capability of its own.

## 5. Success criteria (for the product, once phases land)

- A connected Google Workspace account can be scanned end-to-end into a normalized inventory with no write access used.
- Recommendations are explainable: each one carries a rationale and confidence score a non-technical founder can read and judge.
- No execution-engine action runs without a prior explicit approval captured in the audit log.
- Swapping the underlying LLM provider requires a Gateway-level config/adapter change only — zero changes to `apps/backend` or `apps/worker` call sites.
- A second storage connector (post-Google-Workspace) can be added without changes to the scanner, recommendation engine, or execution engine — only a new `StorageConnector` implementation.

## 6. Out of scope for Phase 0

No application or business logic, no Google Drive integration, no AI Gateway implementation, no frontend, no backend implementation. Phase 0 delivers structure and documentation only — see Engineering Handbook §2 and the Phase 0 Definition of Done below.

## 7. Assumptions & constraints

- Single organization/tenant in early phases, but every data model is written tenant-scoped from day one (Engineering Handbook §13) so multi-tenancy is additive later, not a rewrite.
- Google Workspace is the reference connector; its OAuth scopes, API quotas, and pagination model are the first real-world constraints the Storage Scanner phase has to design against.
- Polyglot monorepo (Engineering Handbook §11): TypeScript/Node.js for `apps/frontend` and its TS packages, Python for `apps/backend`/`apps/worker` and `packages/shared` — revised from the original TypeScript-everywhere assumption by [ADR-012](03_ARCHITECTURE_DECISIONS.md#adr-012-revise-phase-1-stack-vite--react-frontend-fastapi--celery-backendworker) at the start of Phase 1 implementation.

## 8. Phase 0 Definition of Done

- [x] Repository structure matches the architecture in the Engineering Handbook §5.
- [x] Engineering Handbook, Project Master, CTO Dashboard, and Architecture Decision Log exist and are internally consistent with each other.
- [x] Git strategy and branch naming are documented.
- [x] Security philosophy is documented.
- [x] AI Gateway philosophy and architecture are documented.
- [x] Roadmap (this document, §4) aligns with the phase list in `Docs/phases/`.
- [x] CTO Dashboard reflects Phase 0 as the current sprint.
- [x] No application or business logic exists in `apps/*` or `packages/*` — placeholders only.
