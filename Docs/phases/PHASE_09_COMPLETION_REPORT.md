# Phase 9 — Completion Report

**Phase:** [`PHASE_09.md`](PHASE_09.md) — Automation Engine & Workflow Platform
**Status:** Implemented by Claude. Awaiting founder manual test and CTO review (Engineering Handbook §4 lifecycle) before being marked complete in [`01_PROJECT_MASTER.md`](../01_PROJECT_MASTER.md).
**Date:** 2026-08-04

---

## 1. Read this first — the architectural decisions this phase required

**ADR-021 — Automation Engine design.** The phase spec asks for a workflow orchestration platform — a node-graph Workflow Builder, scheduled/event/manual triggers, a Policy Engine, a workflow execution engine with retry/resume/branching, seamless (never-bypassing) integration with Phase 8's Approval System, a Notification Framework, starter templates, and full draft/published/version-history workflow versioning. Two binding founder decisions shaped everything: **policy-gated auto-execution is allowed** (a published policy can auto-approve an `EXECUTE_ACTION` node without a per-instance human click, but creating/publishing that policy always requires a human, and every auto-execution still produces the exact same audited `ApprovalDecision` a human's click would — a policy is a second *kind* of approver, never a bypass) and **email notifications stay stubbed** (the full channel interface is built and tested; no real email is ever sent this phase, matching ADR-018's precedent for the LLM completion provider). The resulting architecture: `ApprovalDecision` gained a nullable `decided_by_policy_id` alongside `decider_user_id`; `ExecutionPlanService` and `ApprovalService` moved from `apps/backend` into `packages/shared` so the worker's `EXECUTE_ACTION` node can call them directly (mirroring ADR-015's DB-layer promotion), with Celery-enqueue side effects constructor-injected so neither app imports the other's code; a real, DB-polled scheduler (not Celery Beat's static crontab config) fires scheduled triggers via an atomic claim-then-reschedule pattern; and only 4 of the spec's 7 named event triggers are wired to a real firing hook, documented explicitly. See [ADR-021](../03_ARCHITECTURE_DECISIONS.md#adr-021-automation-engine-phase-9--policies-as-a-second-kind-of-approver-promoting-execution-engine-services-to-packagesshared-and-a-db-polled-scheduler) for full reasoning, including two real bugs the test suite caught before this phase was considered done.

## 2. Repository changes

```text
packages/shared/vault_shared/
  db/models/
    workflow.py                   NEW — Workflow (+ WorkflowStatus), organization-scoped
    workflow_version.py           NEW — WorkflowVersion (+ WorkflowVersionStatus: draft/published/superseded)
    workflow_node.py               NEW — WorkflowNode (+ WorkflowNodeType), JSONB config + next_nodes
    workflow_trigger.py            NEW — WorkflowTrigger (+ WorkflowTriggerType, WorkflowEventType)
    scheduler_job.py                NEW — SchedulerJob, 1:1 with a SCHEDULED WorkflowTrigger
    workflow_execution.py          NEW — WorkflowExecution (+ WorkflowExecutionStatus), no
                                   PARTIALLY_COMPLETED (a run is one path through a graph, not
                                   independent steps)
    workflow_node_execution.py     NEW — WorkflowNodeExecution (+ WorkflowNodeExecutionStatus,
                                   including WAITING_APPROVAL/WAITING_DELAY)
    workflow_policy.py             NEW — WorkflowPolicy (+ WorkflowPolicyEffect, WorkflowPolicyStatus),
                                   versioned by (organization_id, policy_key)
    notification.py                NEW — Notification (+ NotificationChannel, NotificationStatus)
    automation_template.py         NEW — AutomationTemplate, organization_id NULL = global/seeded
    approval_request.py             + workflow_node_execution_id (nullable, unique); execution_plan_id
                                   now nullable; CHECK constraint relaxed to "at least one" (not
                                   exactly one) — see ADR-021
    approval_decision.py            + decided_by_policy_id (nullable); decider_user_id now nullable;
                                   CHECK constraint "exactly one decider"
  db/repositories/
    workflow_repository.py, workflow_version_repository.py, workflow_node_repository.py,
    workflow_trigger_repository.py, scheduler_job_repository.py (claim_due: atomic UPDATE...RETURNING),
    workflow_execution_repository.py, workflow_node_execution_repository.py,
    workflow_policy_repository.py, notification_repository.py,
    automation_template_repository.py                                      NEW — one per model above
    approval_request_repository.py  + workflow_node_execution_id support in create()/get_by_
                                   workflow_node_execution
    approval_decision_repository.py + create_by_policy() alongside the existing human create()
    user_repository.py              + list_for_organization_by_roles (resolves a notification/approval
                                   node's "recipients": ["owner","admin"] config into real users)
    workflow_trigger_repository.py  list_enabled_by_event_type now organization-scoped (joins Workflow)
  execution/
    plan_service.py                 MOVED from apps/backend/app/application/execution_plan_service.py
                                   (unchanged) — see ADR-021
    approval_service.py             MOVED from apps/backend, extended: workflow-node-scoped decide(),
                                   auto_decide_via_policy(); enqueue callbacks constructor-injected
  notifications/
    providers.py                    NEW — EmailProvider protocol, StubEmailProvider (founder's binding
                                   choice — logs, never sends)
    dispatcher.py                   NEW — NotificationDispatcher: creates the Notification row first,
                                   then attempts delivery ("record before act")
  workflow_events.py                NEW — fire_workflow_event(): shared event-trigger firing logic,
                                   called from both apps
  scheduling.py                     NEW — next_cron_run(): croniter + SCHEDULER_TIMEZONE, shared by
                                   WorkflowTriggerService and SchedulerService
  settings.py                       + workflow_max_retries, workflow_timeout_seconds,
                                   scheduler_timezone, notification_email_enabled,
                                   default_approval_timeout_hours

apps/backend/app/
  application/
    workflow_service.py             NEW — WorkflowService: create, get_detail, get_or_create_draft
                                   (clones nodes from the published version), replace_nodes (client-key
                                   → real-id translation, graph validation), publish, rollback_to_version,
                                   set_status, clone
    workflow_trigger_service.py     NEW — WorkflowTriggerService: create (validates cron/event_type,
                                   seeds SchedulerJob), list, set_enabled
    workflow_policy_service.py      NEW — WorkflowPolicyService: create_draft (auto-versioning),
                                   publish (archives the prior published version), archive
    workflow_execution_service.py   NEW — backend control surface: get/list/detail, trigger_manual,
                                   cancel/pause/resume (mirrors ExecutionJobService's role exactly)
    notification_service.py         NEW — read-only list_for_user
    automation_template_service.py  NEW — list_available, apply (creates a new workflow + draft
                                   seeded from the template's node graph)
    execution_plan_service.py       REWRITTEN — thin re-export of the moved vault_shared class
    approval_service.py             REWRITTEN — thin subclass injecting this app's real Celery producers
    connector_service.py             + fires the connector_reconnected event after a successful connect
  infrastructure/queue/
    workflow_producer.py            NEW — enqueue_workflow_execution
  presentation/
    api/v1/workflows.py             NEW — 13 endpoints: CRUD, versions, draft, node replace, publish,
                                   rollback, status, clone, triggers (+enabled toggle)
    api/v1/workflow_executions.py   NEW — 8 endpoints: manual trigger (rate-limited), list/detail,
                                   cancel/pause/resume
    api/v1/workflow_policies.py     NEW — 6 endpoints: create, list, detail, versions, publish, archive
    api/v1/notifications.py         NEW — GET /notifications
    api/v1/automation_templates.py  NEW — list, apply
    api/v1/schemas.py                + ~20 new Pydantic response/request classes
    dependencies/services.py         + 6 new DI getters
    router.py                        + 5 new router registrations
  alembic/versions/0009_automation_engine_tables.py   10 new tables, approval_requests/
                                   approval_decisions ALTERs, 6 seeded global AutomationTemplate rows

apps/worker/worker/
  workflow/
    execution_service.py            NEW — WorkflowExecutionService: the node execution engine (see §5)
    scheduler_service.py            NEW — SchedulerService: claims + fires due SCHEDULED triggers
  tasks/
    workflow.py                     NEW — worker.workflow.run Celery task, no retry
    scheduler.py                    NEW — worker.scheduler.sweep Celery task (Beat-triggered)
  tasks/scan.py, enrichment.py, recommendation.py   + event-trigger firing hooks
  celery_app.py                     + beat_schedule (60s sweep), 2 new task modules in include

packages/types/src/workflow.ts      NEW — every Workflow/Trigger/Execution/Policy/Notification/
                                   Template shape
packages/types/src/index.ts          + re-exports

apps/frontend/src/
  routes/workflows.tsx                        NEW — Workflow Library (list, create)
  routes/workflows.$workflowId.tsx            NEW — Workflow Detail (versions, triggers/Scheduler UI,
                                   manual trigger, publish, pause/disable/clone)
  routes/workflows.$workflowId.builder.tsx    NEW — Workflow Builder (JSON node-graph editor, not
                                   drag-and-drop — spec explicitly allows this)
  routes/workflow-executions.tsx              NEW — Execution History (+ Failed runs filter)
  routes/workflow-executions.$workflowExecutionId.tsx   NEW — Execution detail + Execution Log
                                   (node timeline) + pause/resume/cancel controls
  routes/workflow-policies.tsx                NEW — Policy Manager
  routes/automation-templates.tsx             NEW — Templates Gallery
  routes/notifications.tsx                    NEW — Notification inbox
  routes/automation.tsx                       NEW — Automation Dashboard (overview + counts)
  routes/dashboard.tsx                         + "Automation" nav link
  lib/workflow-style.ts (+ .test.ts)          status/label helpers, pure, unit-tested
  lib/api-client.ts                            + put() method (needed for node-replace PUT)

tests/unit/backend/test_workflows_router.py, test_workflow_executions_router.py,
  test_workflow_policies_router.py, test_notifications_router.py,
  test_automation_templates_router.py                                       NEW — 15+12+9+2+5 = 43 tests
tests/integration/backend/test_workflow_service_integration.py,
  test_approval_service_workflow_integration.py                            NEW — 11 + 5 = 16 tests
tests/unit/worker/test_workflow_condition_and_policy.py                    NEW — 12 tests, pure logic
tests/integration/worker/test_workflow_execution_service_integration.py,
  test_scheduler_service_integration.py                                    NEW — 7 + 4 = 11 tests
```

## 3. Database changes

Migration `0009_automation_engine_tables` (on top of Phase 8's `0008_execution_engine_tables`):

- **`workflows`** — organization-scoped, plain `active`/`paused`/`disabled` lifecycle. No `published_version_id` column (avoids a circular FK with `workflow_versions`) — "the currently published version" is derived by querying `WorkflowVersion` for `(workflow_id, status=PUBLISHED)`, a service-layer-enforced single-active invariant.
- **`workflow_versions`** — `draft`/`published`/`superseded`. At most one `PUBLISHED` row per workflow (service-enforced); "rollback" is republishing an old `SUPERSEDED` row.
- **`workflow_nodes`** — real rows per the spec's own DB entity list, not a JSONB blob. `next_nodes` (JSONB outcome→node-id map) lives on the node that owns the edge.
- **`workflow_triggers`** — `scheduled`/`event`/`manual`; `config` JSONB holds a cron expression or event-type name.
- **`scheduler_jobs`** — 1:1 bookkeeping for a `SCHEDULED` trigger (`next_run_at`/`last_run_at`/`last_workflow_execution_id`), kept separate from `workflow_triggers` per the spec's own entity list.
- **`workflow_executions`** — one run of a published version; `cancel_requested`/`pause_requested` cooperative flags (mirrors `ExecutionJob`); `context` JSONB carries data between nodes.
- **`workflow_node_executions`** — per-node history within a run; not literally named in the spec's DB Deliverables bullet list but required for "persist execution state"/"resume interrupted workflows"/Execution Logs — same spec-implied-not-spec-literal addition Phase 8 made for `ExecutionResult`/`RollbackRecord`.
- **`workflow_policies`** — versioned by `(organization_id, policy_key)`; every edit is a new row, full history retained.
- **`notifications`** — one row per actual recipient (a fan-out to N people is N rows).
- **`automation_templates`** — `organization_id IS NULL` rows are global; migration seeds the phase spec's 6 named example templates (Archive Inactive Files, Weekly Storage Health Report, Duplicate Review Workflow, Stale Project Cleanup, Public Sharing Audit, Monthly Knowledge Quality Report) via `op.bulk_insert` — same "seed via migration" precedent `0002` used for the three fixed roles.
- **`approval_requests`** — `execution_plan_id` now nullable; new nullable-unique `workflow_node_execution_id`; CHECK constraint changed from "exactly one" to "at least one" (a workflow-triggered `EXECUTE_ACTION` needing approval sets *both*).
- **`approval_decisions`** — `decider_user_id` now nullable; new nullable `decided_by_policy_id`; CHECK constraint "exactly one decider."

Iterated through the downgrade/edit/reapply cycle twice before any consumer code depended on the schema: once to fix `node_definitions` being double-JSON-encoded in the seed data (`json.dumps()` misused against a JSONB-typed bulk-insert column), and once to fix the `approval_requests` CHECK constraint from exactly-one to at-least-one after discovering the workflow-triggered `EXECUTE_ACTION` case needs both columns set simultaneously. Verified via `alembic upgrade head --sql` and applied for real against the founder's live local Postgres each time.

## 4. API surface

```text
POST   /v1/workflows                                          (owner/admin)   → WorkflowResponse (201)
GET    /v1/workflows                                           (any member)    → list (query: status)
GET    /v1/workflows/{id}                                      (any member)    → WorkflowDetailResponse
GET    /v1/workflows/{id}/versions                             (any member)    → list[WorkflowVersionResponse]
POST   /v1/workflows/{id}/draft                                (owner/admin)   → WorkflowDraftResponse
PUT    /v1/workflows/{id}/versions/{vid}/nodes                 (owner/admin)   → list[WorkflowNodeResponse]
POST   /v1/workflows/{id}/publish                              (owner/admin)   → WorkflowVersionResponse (201)
POST   /v1/workflows/{id}/versions/{vid}/rollback              (owner/admin)   → WorkflowVersionResponse
POST   /v1/workflows/{id}/status                               (owner/admin)   → WorkflowResponse
POST   /v1/workflows/{id}/clone                                (owner/admin)   → WorkflowResponse (201)
POST   /v1/workflows/{id}/triggers                              (owner/admin)   → WorkflowTriggerResponse (201)
GET    /v1/workflows/{id}/triggers                              (any member)    → list
POST   /v1/workflows/{id}/triggers/{tid}/enabled                (owner/admin)   → WorkflowTriggerResponse

POST   /v1/workflows/{id}/executions        (owner/admin, rate-limited 30/min) → WorkflowExecutionResponse (201)
GET    /v1/workflows/{id}/executions                            (any member)    → list
GET    /v1/workflow-executions                                  (any member)    → list (query: status)
GET    /v1/workflow-executions/{id}                              (any member)    → WorkflowExecutionDetailResponse
POST   /v1/workflow-executions/{id}/cancel                      (owner/admin)   → WorkflowExecutionResponse
POST   /v1/workflow-executions/{id}/pause                       (owner/admin)   → WorkflowExecutionResponse
POST   /v1/workflow-executions/{id}/resume                      (owner/admin)   → WorkflowExecutionResponse

POST   /v1/workflow-policies                                    (owner/admin)   → WorkflowPolicyResponse (201)
GET    /v1/workflow-policies                                    (any member)    → list
GET    /v1/workflow-policies/{id}                                (any member)    → WorkflowPolicyResponse
GET    /v1/workflow-policies/by-key/{key}/versions                (any member)    → list
POST   /v1/workflow-policies/{id}/publish                       (owner/admin)   → WorkflowPolicyResponse
POST   /v1/workflow-policies/{id}/archive                       (owner/admin)   → WorkflowPolicyResponse

GET    /v1/notifications                                        (any member, own only) → list

GET    /v1/automation-templates                                 (any member)    → list
POST   /v1/automation-templates/{id}/apply                       (owner/admin)   → WorkflowResponse (201)
```

`POST /v1/workflows/{id}/executions` (manual trigger) is the one execution-starting action named explicitly in the phase spec's Security Requirements ("Rate limiting for scheduled jobs") — limited to 30/minute per client IP via the existing `rate_limiter` dependency (scheduled/event triggers are already bounded by the scheduler's own 60s sweep and the "one active run per workflow" check, so they didn't need a second layer). All 25 endpoints verified live: real workflow created → draft fetched → 3-node graph (trigger→notification→end) saved with client-key-to-real-id translation confirmed correct → published → manually triggered → the worker's real execution engine run directly against the same Postgres, producing a real, sent `Notification` row and a `COMPLETED` execution with all 3 `WorkflowNodeExecution`s recorded — confirmed both via direct DB inspection and via `GET /v1/workflow-executions/{id}` and `GET /v1/notifications`. Template application and policy creation were also exercised live.

## 5. Worker behavior

**`WorkflowExecutionService.run(workflow_execution_id)`** (`apps/worker/worker/workflow/execution_service.py`) walks a published `WorkflowVersion`'s node graph one node at a time from `WorkflowExecution.current_node_id`/`.context`, persisting state after every step so a crash or a deliberate pause always resumes from exactly where it left off. Each node type:

- **TRIGGER** — no-op entry marker.
- **CONDITION**/**DECISION** — a tiny, safe structured expression language (`field`/`op`/`value`; `eq`/`ne`/`gt`/`gte`/`lt`/`lte`/`in`/`contains`) evaluated against the run's `context` dict — never `eval()`. `CONDITION` branches `true`/`false`; `DECISION` evaluates an ordered list of named branches.
- **AI_EVALUATION** — calls `AIGateway.complete()` (still the Phase 6 extractive stub) and writes the response into `context` under a configured key.
- **APPROVAL** — creates a real `ApprovalRequest` scoped to this node's `WorkflowNodeExecution`, notifies the configured recipients, and pauses (`WAITING_APPROVAL`). Resuming reads the request's final status and branches on `approved`/`rejected`/`changes_requested` (or falls back to `default`).
- **EXECUTE_ACTION** — the Phase 8 integration point. Resolves a published `WorkflowPolicy` by key, finds the org's current `ACTIVE` recommendation matching the configured rule, and dispatches on the policy's effect: `SKIP` (no plan ever built), `REQUIRE_APPROVAL` (builds a real `ExecutionPlan`+`ApprovalRequest` via the now-shared `ExecutionPlanService`, links the same request to this node, pauses), or `AUTO_EXECUTE` (builds the plan, immediately calls `ApprovalService.auto_decide_via_policy`, which creates the policy-attributed decision and a real `ExecutionJob`, enqueued exactly like a human approval would). A recommendation that doesn't match the policy's conditions, or doesn't exist this run, is a `SKIPPED` node outcome, not a failure.
- **DELAY** — computes a `resume_at` timestamp, marks `WAITING_DELAY`, and schedules a Celery-countdown continuation of `worker.workflow.run` for itself — never an in-process `sleep()`, so a long delay never ties up a worker.
- **NOTIFICATION** — resolves recipients (role names like `"owner"` or explicit user ids) via `UserRepository.list_for_organization_by_roles`, then calls the shared `NotificationDispatcher` once per recipient.
- **END** — terminal; the run loop naturally stops once `next_nodes` resolves to nothing.

Two real bugs were caught by the test suite before this phase shipped (not live) — see ADR-021's Consequences: the `ApprovalRequest` exactly-one-target constraint (caught during design) and a node returning the internal "waiting" sentinel never actually setting `WorkflowExecution.status` to `PAUSED` (caught by an integration test asserting the status directly) — both fixed and covered by regression tests.

**`SchedulerService.run_due()`** (`worker/workflow/scheduler_service.py`), invoked every 60 seconds by a fixed Celery Beat entry (`worker.scheduler.sweep`), atomically claims every due `SchedulerJob` (`SchedulerJobRepository.claim_due`'s single `UPDATE ... RETURNING`), starts a fresh `WorkflowExecution` for each one whose workflow is still active with a published version and no run already in progress, and — regardless of whether firing succeeded, was skipped, or failed — always recomputes and persists the trigger's next `croniter` occurrence, so a claimed row is never silently orphaned.

Event triggers (`vault_shared.workflow_events.fire_workflow_event`) are wired into 4 real completion boundaries: `worker/tasks/scan.py` (`scan_completed`), `enrichment.py` (`enrichment_completed`), `recommendation.py` (`recommendation_generated`), and the backend's `ConnectorService.complete_connect` (`connector_reconnected`) — each a small addition at an already-existing chain point, resolving the firing organization (directly for the org-scoped `RecommendationJob`, through the connector for connector-scoped jobs).

## 6. Workflow, policy, and automation logic

Policies gate `EXECUTE_ACTION` nodes with three effects (`SKIP`/`REQUIRE_APPROVAL`/`AUTO_EXECUTE`) and a recommendation-level condition check (`max_affected_files`, `min_confidence`) — a documented, coarser stand-in for the spec's per-file examples ("skip actions on executive folders"), which would require extending Phase 8's `ExecutionPlanService.create_plan` itself; deferred, not built this phase. Every policy edit is a new, fully-retained version; publishing archives whatever was previously published for the same key — the same versioning discipline workflows themselves get.

Six global automation templates were seeded, matching the phase spec's own named examples, each a real, valid node graph (trigger → …→ end) using only implemented node types; the three referencing `EXECUTE_ACTION` (Archive Inactive Files, Duplicate Review Workflow, Stale Project Cleanup) leave `policy_key` blank for the founder to fill in after applying, since a policy is always organization-specific and can't be seeded generically.

## 7. Tests and what was actually verified in this environment

- **Backend:** 310 tests total (59 new — 43 unit across five new routers, `TestClient` + `dependency_overrides`, same pattern as every prior phase; 16 integration against real Postgres covering `WorkflowService` — draft/publish/rollback/clone/graph-validation — `WorkflowPolicyService`'s versioning, and `ApprovalService`'s three new decision shapes: a plain workflow-node approval resuming with no job, an `EXECUTE_ACTION` approval both creating a job and resuming the workflow, and a policy-attributed auto-decision). The entire pre-existing Phase 8 suite (251 tests) was rerun unmodified after moving `ExecutionPlanService`/`ApprovalService` into `packages/shared`, confirming the move was fully transparent. `ruff`/`mypy` clean across the full `app` package (77 files) and the full `vault_shared` package (135 files).
- **Worker:** 130 tests total (23 new — 12 unit for the condition-evaluation/policy-matching pure logic; 11 integration against real Postgres covering the full node execution lifecycle: notification delivery, condition branching on seeded context, an AI-evaluation node calling the real stubbed gateway, an approval node pausing then resuming on the correct branch, an execute-action node being skipped with no policy, an execute-action node auto-executing via a real published policy and producing a real `ExecutionPlan`/`ExecutionJob`, cooperative cancellation of a paused run, and four scheduler scenarios — firing a due trigger and rescheduling it, skipping a paused workflow while still rescheduling, not double-firing an already-claimed trigger, and skipping an unpublished workflow). `ruff`/`mypy` clean across the full worker package (32 files).
- **Frontend:** `tsc --noEmit`, `eslint .`, and a full `vite build` clean on all 9 new routes, confirmed via the generated route tree and per-route code-split chunks. 89 vitest tests total (13 new — `workflow-style.ts`). Same one pre-existing, unrelated vitest failure noted in every phase since Phase 7 (`google-sign-in-button.test.tsx`, caused by a local `.env` file predating this session) — not a regression.
- **Live, not just mocked.** Every DB-only backend path was exercised end-to-end via real HTTP against a real running backend and real Postgres: workflow creation, draft fetch, a 3-node graph save (confirming client-key-to-real-UUID translation), publish, manual trigger (creating a real, `PENDING` `WorkflowExecution`), template listing and application, and policy creation. The worker's actual node execution engine was then run directly (no real Celery consumer needed to be started, matching the established "no real writes" testing discipline) against that same real execution, producing a genuinely `COMPLETED` run with all 3 nodes recorded and a real `Notification` row with `status: "sent"` — confirmed both by direct repository inspection and by re-fetching through the real API.

**Concrete manual-test steps for the founder**, beyond Phase 1-8's checklist: create a workflow, open the builder, add a trigger → notification → end graph, save, publish, and manually trigger it — confirm it completes and a notification appears at `/notifications`; create a scheduled trigger with a near-future cron expression and confirm it fires within about a minute (worker + Celery Beat must both be running for this); create a policy with `require_approval`, build a workflow with `execute_action` referencing a real executable recommendation rule (`duplicate_files`/`archive_candidates`/`large_unused_files`) and that policy, trigger it, and confirm it pauses at `/workflow-executions` and a real `ApprovalRequest` appears at `/approvals`; approve it and confirm the workflow resumes and completes; separately, publish a policy as `auto_execute` and confirm triggering that workflow creates and queues an `ExecutionJob` with no approval-queue entry required, while still showing a full audit trail attributing the decision to the policy, not a person; try the Templates Gallery, apply a template, and confirm it lands as an editable draft.

## 8. Known limitations / follow-ups

- Same `packages/types` manual-sync caveat as every prior phase (ADR-012), now also covering `workflow.ts`.
- **`WorkflowPolicy.conditions` gate at the recommendation level, not per-file** — the spec's "skip actions on executive folders"/"never modify legal documents" examples describe per-file filtering not built this phase; see ADR-021.
- **Only 4 of 7 named event trigger types have a real firing hook** — `file_added`, `file_updated`, `storage_threshold_exceeded` are modeled/configurable but never fire. Documented, not an oversight.
- **Schedule accuracy is bounded by the 60-second sweep interval**, not exact-to-the-second.
- **Email notifications are fully stubbed** — the channel, delivery-status tracking, and UI are all real and tested, but no real email is ever sent (the founder's binding choice this phase).
- **The Workflow Builder is a JSON-editing form, not a drag-and-drop canvas** — explicitly allowed by the phase spec ("the interface should support drag-and-drop in a future iteration, but the backend should not depend on it").
- **No monitoring metrics were added** (workflow success rate, average execution duration, queue depth, trigger frequency, notification delivery success) — named in the phase spec's Logging & Observability section, not built this phase; same category of gap already logged for Phase 8's execution metrics.
- **No Docker/infrastructure changes for a separate Celery Beat container** — the phase spec's Infrastructure Deliverables mention "Add scheduler service (if implemented separately)"; this phase adds the `beat_schedule` config to the existing worker's `celery_app.py` but does not add a dedicated `docker-compose` service definition to run `celery beat` as its own container. A founder running this locally needs to start `celery -A worker.celery_app beat` as a separate process alongside the existing worker.
- **`ExecutionPlanService`/`ApprovalService` now live in `packages/shared`, read from both apps** — a new instance of the "promote to shared once a second app needs it" pattern ADR-015 established; noted in ADR-021 as worth watching for recurrence.
- Route components remain outside the automated test suite by consistent design choice — standing item in the CTO Dashboard's Technical Debt.
- Phase roadmap numbering (this phase's content matches its actual filename for the first time — `PHASE_09.md` — but the founder's standing instruction to leave the numbering caveat unresolved elsewhere still applies to Phases 1-8).

## 9. Recommendation for Phase 10

Per this phase's own document, Phase 10 is Production Hardening, Security & Enterprise Release — security hardening, performance optimization, production deployment, disaster recovery, compliance, scalability, and a final release checklist. The technical-debt list accumulated across Phases 8 and 9 is a natural, concrete input: rate limiting exists only on two endpoint families (Phase 8 never got it, Phase 9's manual-trigger got it) and should be audited and applied consistently across every mutating endpoint; monitoring/metrics were named in both Phase 8 and Phase 9's specs and never built — Phase 10's "production hardening" framing is exactly where that belongs; the Celery Beat scheduler needs a real deployment story (a dedicated container/process, health checks, and what happens if it's down — scheduled triggers simply don't fire, silently, until it's back, which needs to be either monitored or made more resilient); and the `packages/types` manual-sync gap (flagged every phase since ADR-012) is worth finally addressing with codegen before "enterprise release" implies external API consumers who'd notice drift. On the product side, the two founder-gated capabilities this phase built but left dormant by default — policy-driven auto-execution and real email delivery — are exactly the kind of thing a production release checklist should force a deliberate, documented decision on (per-organization, not global) rather than leaving as an implicit "nobody's configured this yet."
