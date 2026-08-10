# 13 — Release Notes: Version 1.0

Status: **Point-in-time document**, written at the close of Phase 10. Update at each future major release rather than rewriting this one — treat this as the V1.0 entry in what should become a running log.

---

## AI Project Vault — Version 1.0

An intelligence layer over an organization's storage (starting with Google Workspace): it scans, understands, recommends, and — with explicit human approval — acts on what it finds. Version 1.0 covers ten development phases, from the engineering blueprint through production hardening.

### What's included

**Foundation & Identity**
- Polyglot monorepo (Vite/React frontend, FastAPI/Celery backend/worker, PostgreSQL, Redis).
- Google Identity Services sign-in, JWT + rotating-refresh-cookie sessions, role-based access control (owner/admin/member), organization management.

**Storage Connection & Discovery**
- Google Workspace connector with its own server-side OAuth flow, encrypted token storage, automatic token refresh.
- A provider-agnostic, read-only storage scanner — full and incremental sync, cancellable, retryable.

**Understanding**
- A deterministic Knowledge Engine: content extraction (PDF, Office formats, Google-native Docs/Sheets/Slides), classification, naming-pattern/ownership/sharing signals, cross-file relationship discovery.
- An AI Gateway-backed intelligence layer: free/offline local embeddings, hybrid metadata+semantic search, RAG-style conversational querying with citations. The completion (chat-answer-generation) side is deliberately stubbed to a deterministic, never-invents-an-answer fallback — no real LLM provider is connected yet, a founder decision, not a technical limitation.

**Recommending**
- An organization-scoped Recommendation Engine — 11 deterministic rules across storage, knowledge, security, collaboration, and productivity, plus 2 insight generators, with explainable confidence scoring.
- The Founder Command Center dashboard — organization overview, storage/knowledge health, an AI insights feed, historical trend data.

**Acting**
- The Execution Engine & Human Approval System — every recommended action becomes a deterministic, auditable plan; nothing executes without an explicit, individually-recorded human approval. Actions supported: move, rename, archive, remove-duplicate, update-metadata — no permanent deletion (Google Drive's own Trash, always recoverable).
- The Automation Engine & Workflow Platform — a node-graph workflow builder, scheduled/event/manual triggers, and a versioned Policy Engine where a specific, narrowly-scoped, owner/admin-authored policy can auto-approve a recurring action *without* a per-instance click — while still producing the exact same audited approval record a human's decision would. Automation is a second kind of approver, never a bypass of the Approval System.

**Production Readiness (this phase)**
- Security hardening: response security headers, expanded rate limiting, dependency vulnerability scanning (two real CVEs found and fixed), a documented threat model.
- Observability: Prometheus metrics, OpenTelemetry tracing and Sentry error tracking (both off until a real endpoint/DSN is configured), structured logging with request/task correlation IDs spanning both the API and background-job layers.
- Reliability: liveness/readiness probes, graceful shutdown, a documented and intentional per-task-type retry policy.
- Backup & disaster recovery: automated backup/restore scripts, drilled for real against production-scale local data with a 100% match across all 53 database tables.
- Infrastructure as code: a complete, validated Terraform reference implementation (AWS) for staging and production — network, database, cache, load balancer, compute, secrets, monitoring.
- A completed CI/CD pipeline: lint, typecheck, unit+integration tests, dependency/secret/image scanning, and gated deployment automation with automatic rollback on failure.

### Known limitations (see the [Release Readiness Report](phases/PHASE_10_COMPLETION_REPORT.md) for the full list)

- No real LLM completion provider is connected — chat answers are deterministic and extractive, not generative, until a founder chooses and configures one.
- Email notifications are fully built but stubbed — no real email is sent yet.
- Only 3 of 11 recommendation rules currently have a matching executable action.
- Only 4 of 7 named automation event-trigger types have a real firing hook.
- Deployment infrastructure (Terraform, Docker images, CI's deploy job) is validated but has not been applied against a real cloud account or exercised end-to-end, since none exists in this project's development environment.

### Upgrade notes

This is the first Version 1.0 release — there is no prior version to upgrade from. Future releases should log migration steps, breaking changes, and deprecations here.

### Acknowledgments

Built across ten phases following a fixed engineering lifecycle: CTO-authored phase specifications, full-phase implementation passes, and founder manual QA at each step — documented in full in the [ADR log](03_ARCHITECTURE_DECISIONS.md) and each phase's own completion report under `Docs/phases/`.
