# Phase 8 — Completion Report

**Phase:** [`PHASE_08_SECURITY_RELEASE.md`](PHASE_08_SECURITY_RELEASE.md) — Execution Engine & Human Approval System (filename is stale — see Technical Debt in the CTO Dashboard; the document's own in-text content is the Execution & Approval System, not a security/release phase)
**Status:** Implemented by Claude. Awaiting founder manual test and CTO review (Engineering Handbook §4 lifecycle) before being marked complete in [`01_PROJECT_MASTER.md`](../01_PROJECT_MASTER.md).
**Date:** 2026-08-03

---

## 1. Read this first — the architectural decisions this phase required

**ADR-020 — Execution Engine design.** The phase spec asks for a provider-agnostic execution platform that turns an approved `Recommendation` into a deterministic, reviewable `ExecutionPlan`, gates every action behind explicit human approval, executes only through the Connector Platform, verifies the result, and supports rollback where possible — explicitly forbidding permanent deletion and any autonomous/recurring scheduling (Phase 9's content) this phase. One design question was the founder's, not Claude's to infer: whether any of this phase's own verification work may perform a real mutating call against the founder's actual connected Google Drive account. The founder chose **no real writes — fakes/mocks only**, binding for every test and manual smoke-check in this phase. The resulting architecture: the OAuth scope bumps to full `drive` write access only now, for the first time (Handbook §13 least-privilege timing); `ARCHIVE`/`REMOVE_DUPLICATE` use Drive's own Trash, never `files.delete`, which is what makes rollback available by default; `ExecutionPlan.risk_level` is a distinct blast-radius computation from `Recommendation.risk_level`; `ExecutionJob.is_rollback` reuses one job/service/audit machinery for both forward execution and reversal instead of a parallel job type; a `RollbackRecord` is committed *before* the live mutation it protects against; permission validation is a two-tier shared function (approval-time in the backend, defense-in-depth in the worker); and only 3 of Phase 7's 11 recommendation rules map to a supported execution action, via an explicit, narrow allowlist that rejects everything else with a clear error rather than silently doing nothing. See [ADR-020](../03_ARCHITECTURE_DECISIONS.md#adr-020-execution-engine-phase-8--drive-trash-instead-of-deletion-org-scoped-plans-reusing-the-jobrollback-machinery-and-a-narrow-ruleaction-allowlist) for full reasoning and alternatives considered.

## 2. Repository changes

```text
packages/shared/vault_shared/
  connectors/google_drive.py    + get_file, move_file, rename_file, set_trashed, update_app_properties
                                 (write-capable methods); _request() now dispatches PATCH/POST via a new
                                 method param; new NotFoundError branch on a 404 response
  settings.py                    google_workspace_scopes → full `drive` write scope (was `drive.readonly`);
                                 + execution_max_retries, execution_timeout_seconds, approval_expiry_hours,
                                 execution_rollback_enabled
  formatting.py                  NEW — human_bytes() moved here from apps/worker/worker/recommendation/
                                 formatting.py so both the Recommendation Engine and Execution Planner share it
  execution/
    __init__.py                  NEW — exports DRIVE_WRITE_SCOPE, validate_execution_permissions
    permission_validation.py     NEW — validate_execution_permissions(connector, credentials): the DB-only
                                 half of Phase 8's permission checklist, shared by backend + worker
  db/models/
    execution_plan.py            NEW — ExecutionPlan (+ ExecutionPlanStatus), organization-scoped
    execution_step.py            NEW — ExecutionStep (+ ExecutionActionType, ExecutionStepStatus)
    approval_request.py          NEW — ApprovalRequest (+ ApprovalStatus), unique on execution_plan_id
    approval_decision.py         NEW — ApprovalDecision (+ ApprovalDecisionType), append-only
    execution_job.py             NEW — ExecutionJob (+ ExecutionJobStatus), is_rollback flag,
                                 triggered_by_user_id, cancel_requested/pause_requested cooperative flags
    execution_result.py          NEW — ExecutionResult (+ ExecutionResultStatus, VerificationStatus),
                                 indexed but NOT unique on execution_step_id (a rollback job records its own
                                 result for a step a forward job already has one for)
    rollback_record.py            NEW — RollbackRecord, unique on execution_step_id (one canonical
                                 pre-mutation snapshot per step)
    execution_audit.py           NEW — ExecutionAudit, append-only, execution-specific audit trail
  db/repositories/
    execution_plan_repository.py, execution_step_repository.py, approval_request_repository.py,
    approval_decision_repository.py, execution_job_repository.py, execution_result_repository.py,
    rollback_record_repository.py, execution_audit_repository.py         NEW — one per model above

apps/backend/app/
  application/
    execution_plan_service.py    NEW — ExecutionPlanService: create_plan (rule→action allowlist, risk
                                 computation, step generation, approval-request creation, all in one
                                 transaction), get_detail, list_for_organization
    approval_service.py          NEW — ApprovalService: list/get (lazy expiry), decide (single choke point —
                                 permission-checks an approve, creates+enqueues an ExecutionJob only on
                                 approve, terminal reject/request_changes), bulk_decide (per-item isolation)
    execution_job_service.py     NEW — ExecutionJobService: get/list, cancel/pause/resume (cooperative flags),
                                 trigger_rollback (creates a second ExecutionJob with is_rollback=True)
  infrastructure/queue/
    execution_producer.py        NEW — enqueue_execution_job, same Celery-client pattern as every prior stage
  presentation/
    api/v1/execution_plans.py    NEW — POST/GET /execution-plans, GET /{id}, POST /{id}/rollback
    api/v1/approvals.py           NEW — GET /approvals, GET /{id}, POST /{id}/decide, POST /bulk-decide
    api/v1/execution_jobs.py     NEW — GET /execution-jobs, GET /{id}, POST /{id}/cancel|pause|resume
    api/v1/schemas.py             + ExecutionStepResponse, ExecutionPlanResponse/DetailResponse,
                                 CreateExecutionPlanRequest, ApprovalRequestResponse, ApprovalDecisionRequest,
                                 BulkApprovalDecisionRequest, ExecutionJobResponse/DetailResponse,
                                 ExecutionResultResponse
    api/v1/router.py              + execution_plans_router, approvals_router, execution_jobs_router
    dependencies/services.py      + get_execution_plan_service, get_approval_service, get_execution_job_service
  alembic/versions/0008_execution_engine_tables.py   creates all 8 tables above, full downgrade() included

apps/worker/worker/
  execution/
    execution_service.py          NEW — ExecutionService: run() (permission re-check, forward/rollback
                                 dispatch on is_rollback), _run_forward/_execute_forward_step
                                 (rollback-record-before-mutation, per-step failure isolation, verification
                                 recorded separately from step success), _run_rollback/_rollback_one
                                 (mirrors forward, reverses via stored pre_state)
  tasks/execution.py               NEW — worker.execution.run Celery task, no retry (one mutating action
                                 retried blind is a correctness risk this phase declines to take)
  celery_app.py                    + "worker.tasks.execution" in the include list
  recommendation/rules.py          human_bytes import updated to vault_shared.formatting (moved, see above)

packages/types/src/execution.ts    NEW — ExecutionActionType/Step/PlanStatus/RiskLevel/Plan/PlanDetail,
                                 CreateExecutionPlanRequest, ApprovalStatus/Request/DecisionType/
                                 DecisionRequest, BulkApprovalDecisionRequest, ExecutionJobStatus/Job/Detail,
                                 ExecutionResultStatus/VerificationStatus/Result
packages/types/src/index.ts        + re-exports

apps/frontend/src/
  routes/execution-plans.tsx               NEW — Execution Center: status-filtered plan list
  routes/execution-plans.$executionPlanId.tsx  NEW — Plan Viewer + Risk Summary + step list + Rollback trigger
  routes/approvals.tsx                     NEW — Approval Queue: per-row decide (approve/reject/request
                                 changes) with a required extra confirmation checkbox before an owner/admin
                                 can approve a high-risk plan, plus bulk-decide with the same high-risk gate
  routes/execution-jobs.tsx                NEW — Execution History + a one-click Failed Jobs filter, cancel
  routes/execution-jobs.$executionJobId.tsx  NEW — Job Progress View + Execution Timeline (per-step results)
                                 + pause/resume/cancel controls
  routes/recommendations.$recommendationId.tsx  + "Create execution plan" action (owner/admin) wired to
                                 POST /v1/execution-plans, replacing the now-stale "never executes
                                 automatically" copy with an accurate approval-gated description
  routes/dashboard.tsx                     + nav links to Execution Center and Approval Queue
  lib/execution-style.ts (+ .test.ts)      planStatusColor/jobStatusColor/approvalStatusColor/riskLevelColor/
                                 isActiveJobStatus/actionTypeLabel — pure, unit-tested

tests/unit/backend/test_execution_plans_router.py, test_approvals_router.py,
  test_execution_jobs_router.py                                                NEW — 11 + 12 + 11 tests
tests/integration/backend/test_execution_service_integration.py                NEW — 15 tests, real Postgres
  (ExecutionPlanService, ApprovalService, ExecutionJobService)
tests/unit/worker/test_execution_pre_mutation_state.py                         NEW — 6 tests, pure logic
tests/integration/worker/test_execution_service_integration.py                 NEW — 5 tests, real Postgres +
  a hand-written fake GoogleDriveClient (forward execution, rollback, per-step failure isolation, permission-
  gate blocking with zero Drive calls made, cooperative cancellation)
```

## 3. Database changes

Migration `0008_execution_engine_tables` (on top of Phase 7's `0007_recommendation_engine_tables`):

- **`execution_plans`** — organization-scoped (like `RecommendationJob`, not connector-scoped), FK to its source `Recommendation`. `risk_level` is this plan's own blast-radius computation (file count), independent of the recommendation's business-risk level. `required_permissions` is a plain JSONB array (currently always `["google_workspace:drive:write"]`).
- **`execution_steps`** — one per affected file, ordered, carrying `pre_state`/`planned_change` JSONB and its own status independent of the plan's.
- **`approval_requests`** — unique on `execution_plan_id` (exactly one approval request per plan, ever), organization-scoped, with a lazily-checked `expires_at` (`approval_expiry_hours`, default 72).
- **`approval_decisions`** — append-only, one row per decision (approve/reject/request_changes), capturing decider, timestamp, comments, and IP address.
- **`execution_jobs`** — has both `cancel_requested` and `pause_requested` cooperative flags (unlike prior job types, which had cancel only), plus `is_rollback` and a nullable `triggered_by_user_id` (the worker has no "current user" concept of its own — the triggering human is stored on the job at creation time). Deliberately has no companion `ExecutionProgress` table — a single execution run is fast with no meaningful "N/M" mid-run progress to report.
- **`execution_results`** — indexed but *not* unique on `execution_step_id`; the real natural key is `(execution_job_id, execution_step_id)`, since a rollback job must record its own outcome for a step a forward job already has a result for.
- **`rollback_records`** — unique on `execution_step_id` (one canonical pre-mutation snapshot per step, regardless of how many jobs later reference it).
- **`execution_audits`** — append-only, execution-specific audit trail (plan/job context columns) alongside the pre-existing generic `AuditLog`, which also gets coarse entries for approval decisions (`execution_approved`/`execution_rejected`/etc.) for the established cross-module "everything sensitive in one place" convention.

Iterated three times via `alembic downgrade 0007` → edit model + migration → `alembic upgrade head --sql` → `alembic upgrade head`, before any consumer code existed against the schema (self-caught gaps: the `execution_results` unique constraint, then `execution_jobs.triggered_by_user_id`) — kept the final migration history as one coherent file rather than stacking patch migrations. Verified via `alembic upgrade head --sql` and applied for real against the founder's live local Postgres instance (`alembic upgrade head` succeeded, `0007 → 0008`).

## 4. API surface

```text
POST   /v1/execution-plans                      (owner/admin)   → ExecutionPlanResponse (201)
GET    /v1/execution-plans                       (any org member) → list[ExecutionPlanResponse] (query: status)
GET    /v1/execution-plans/{id}                  (any org member) → ExecutionPlanDetailResponse (+ steps)
POST   /v1/execution-plans/{id}/rollback         (owner/admin)   → ExecutionJobResponse (201)

GET    /v1/approvals                             (any org member) → list[ApprovalRequestResponse] (query: status)
GET    /v1/approvals/{id}                        (any org member) → ApprovalRequestResponse
POST   /v1/approvals/{id}/decide                 (owner/admin)   → ApprovalRequestResponse
POST   /v1/approvals/bulk-decide                 (owner/admin)   → list[ApprovalRequestResponse]

GET    /v1/execution-jobs                        (any org member) → list[ExecutionJobResponse] (query: status)
GET    /v1/execution-jobs/{id}                   (any org member) → ExecutionJobDetailResponse (+ results)
POST   /v1/execution-jobs/{id}/cancel            (owner/admin)   → ExecutionJobResponse
POST   /v1/execution-jobs/{id}/pause             (owner/admin)   → ExecutionJobResponse
POST   /v1/execution-jobs/{id}/resume            (owner/admin)   → ExecutionJobResponse
```

`POST /v1/execution-plans` validates the source recommendation is `active`, its rule is on the executable allowlist, no other plan is already active for it, and at least one affected file still exists — all from already-stored state, no live Drive call. `POST /v1/approvals/{id}/decide` is the single point every execution passes through: an `approve` decision re-validates permissions (connector connected, write scope present) and only creates+enqueues an `ExecutionJob` if that passes, returning a `422 validation_error` naming exactly what's missing otherwise; `reject`/`request_changes` are terminal, no job created. `POST /v1/execution-plans/{id}/rollback` requires `execution_rollback_enabled` (settings), `rollback_available` on the plan, at least one not-yet-rolled-back `RollbackRecord`, and no other job already active for that plan.

## 5. Worker behavior

`ExecutionService.run(execution_job_id)`: loads the job and its plan, re-resolves the connector and re-runs `validate_execution_permissions` (defense-in-depth — time has passed since the backend's own check at approval time), marks the job `RUNNING` and records an `execution_started` audit entry, sets the plan to `EXECUTING` (forward jobs only), then dispatches on `job.is_rollback`.

**Forward path:** iterates the plan's `ExecutionStep`s in order, skipping any already `COMPLETED`/`FAILED` (resuming after a pause never re-runs a decided step), checking cooperative cancel/pause between each. Per step: loads the target file, does a live `get_file` read (the "resource existence"/"current file state" check — right before mutating, since Drive state can drift after the plan or even after approval), captures and commits a `RollbackRecord` from that live state *before* calling the connector's mutating method, then applies the action. A step's own exception is caught, logged, rolled back at the DB level, and recorded as a `FAILED` `ExecutionResult` without stopping the rest of the plan (the same per-item failure isolation convention every job type since Phase 4 has used). A successful mutation is then separately verified with another live read; a verification failure is recorded on the `ExecutionResult` (`verification_status=FAILED`) but the step itself still counts as `COMPLETED` — the mutation genuinely happened, and auto-rolling-back on a verification disagreement would itself be a second, unreviewed mutating action the spec never asked for. The job/plan finish `COMPLETED`, `PARTIALLY_COMPLETED`, or `FAILED` depending on the succeeded/failed step tally.

**Rollback path:** iterates `RollbackRecordRepository.list_rollbackable_for_plan` (every not-yet-rolled-back record for the plan's steps) in the same cancel/pause-aware loop, reversing each step's action from its stored `pre_state` (un-trash, restore original name, move back to the original parent), marking the record and step rolled back on success. The plan only reaches `ROLLED_BACK` if every rollbackable record succeeded; any failure leaves the job `PARTIALLY_COMPLETED` so a founder can see exactly which files didn't reverse cleanly.

Unlike every prior stage, nothing auto-chains into execution. `worker.execution.run` (`apps/worker/worker/tasks/execution.py`) is only ever enqueued by `ApprovalService.decide`'s approve branch or `ExecutionJobService.trigger_rollback` — both require a human's explicit action first, per the Core Philosophy's "no shortcuts." The Celery task carries no retry policy: a partially-applied mutating action retried blind is a correctness risk this phase declines to take, unlike a safely-idempotent read-only scan/enrichment/embedding retry.

## 6. Execution logic

Only 3 of Phase 7's 11 rules currently produce an executable plan (`ExecutionPlanService._EXECUTABLE_RULES`): `duplicate_files`→`REMOVE_DUPLICATE`, `archive_candidates`/`large_unused_files`→`ARCHIVE`. Both actions are implemented as Drive Trash (`set_trashed`), never `files.delete` — the phase spec's explicit "no permanent deletion" boundary, and the reason `rollback_available` can default to `true` for every plan this phase actually produces. `MOVE_FILE`, `MOVE_FOLDER`, `RENAME`, and `UPDATE_METADATA` are fully implemented in the connector and `ExecutionService` (the phase spec's literal action list) but have no rule that requests them yet — a documented scope boundary, not a bug.

Risk is computed purely from step count (`_risk_level_for`): ≤10 files low, ≤100 medium, >100 high — deliberately distinct from `Recommendation.risk_level`, since every supported action here is fully reversible and the real variable severity between two approvals is blast radius, not the nature of the underlying issue. The frontend's Approval Queue uses this exact field to require an extra explicit confirmation checkbox before an owner/admin can click Approve on a high-risk plan, directly satisfying the spec's "make it impossible to accidentally approve high-risk operations."

Permission validation is split two ways: `validate_execution_permissions` (shared, DB-only — connector connected, credentials present, `https://www.googleapis.com/auth/drive` present in `granted_scopes`) runs at approval time in the backend and again, defense-in-depth, in the worker right before execution; "resource existence"/"current file state" needs a live read and only ever happens in the worker, per-step, immediately before that step's mutation.

## 7. Tests and what was actually verified in this environment

- **Backend:** 251 tests total (49 new — 34 unit tests across three new routers, `TestClient` + `dependency_overrides`, same pattern as every prior router, covering auth/role gating and `ValidationError`/`ConflictError`/`NotFoundError` propagation to the correct HTTP status; 15 new integration tests against real Postgres covering `ExecutionPlanService` — step generation, risk computation at both boundaries, rejection of non-executable rules/resolved recommendations/duplicate plans — `ApprovalService` — the permission-gate blocking an approve, a real approve creating a real `ExecutionJob`, reject being terminal, per-item bulk-decide isolation — and `ExecutionJobService` — cancel/pause/resume status gating, rollback requiring an actual rollbackable record). `ruff` clean; `mypy` clean on all source modules touched (test files follow this codebase's existing convention of not being mypy-annotated, consistent with every prior phase's test files).
- **Worker:** 107 tests total (11 new — 6 unit tests for `ExecutionService._pre_mutation_state`'s pure logic across every action type including the two never-yet-exercised-by-a-rule ones (`RENAME`, `MOVE_FILE`/`MOVE_FOLDER`, `UPDATE_METADATA`); 5 integration tests against real Postgres and a hand-written fake `GoogleDriveClient` — forward execution actually trashing a file and completing job+plan+step+result+rollback-record correctly, a full forward-then-rollback cycle actually un-trashing the file and reaching `ROLLED_BACK`, one file's simulated "no longer exists on Drive" failure not stopping the plan's other step, **the permission gate blocking execution with zero calls made to the fake Drive client at all** — a structural proof, not just a policy statement, that an under-scoped connector can never reach a mutating call — and cooperative cancellation). `ruff` clean; `mypy` clean.
- **Frontend:** `tsc --noEmit`, `eslint .`, and a full `vite build` all clean on the four new routes (`/execution-plans`, `/execution-plans/$id`, `/approvals`, `/execution-jobs`, `/execution-jobs/$id`) plus the updated recommendation detail page — confirmed via the generated route tree and per-route code-split chunks. 76 vitest tests total (18 new — `execution-style.ts`'s status/risk/action-label helpers). One pre-existing, unrelated failure (`google-sign-in-button.test.tsx`, caused by a local `.env` file predating this phase leaking `VITE_GOOGLE_CLIENT_ID` into the test) — not a regression from this phase, confirmed by reproducing it with the variable explicitly unset at the shell level and finding the `.env` file itself is the actual source, dated before this session started.
- **The founder's binding "no real writes" constraint was honored throughout, and verified two independent ways.** Everything that only touches this platform's own database was exercised live: `POST /v1/execution-plans` against a real `duplicate_files` recommendation (17 real affected files) produced a real plan (`"17 files, ~16.5 MB"`, medium risk, 17 steps, a real `ApprovalRequest` with a real 72-hour expiry); a real approve attempt against the founder's actual pre-Phase-8 connector was **correctly rejected** with `"Connector was authorized without Drive write access — reconnect Google Workspace to grant it before this plan can execute"` — proving the real permission gate works and, as a direct consequence, that no real Drive mutation was ever reachable through this session's own testing; a real reject decision then correctly transitioned the approval to `rejected`. Everything that would otherwise call Google Drive — trash/un-trash, live state reads, verification, rollback — was exercised exclusively against a hand-written fake `GoogleDriveClient` (an in-memory dict of files, mutated the same way Drive's own API would) in the integration test suite above, never against the founder's real account. A real Celery worker process was never started during manual smoke-testing this phase — the only way a real job could execute is a founder later reconnecting Google Workspace with write scope and approving a plan themselves through the UI.

**Concrete manual-test steps for the founder**, beyond Phase 1-7's checklist: reconnect Google Workspace via `/storage-connections` (required — the existing connection only has read access); visit a `duplicate_files` or `archive_candidates`/`large_unused_files` recommendation's detail page and click "Create execution plan"; review the resulting plan's risk summary, step list, and required permissions on its detail page; visit `/approvals`, confirm the pending request appears with the plan's risk/impact shown inline; for a high-risk plan, confirm the Approve button stays disabled until the explicit high-risk confirmation checkbox is checked; approve it and confirm it moves into `/execution-jobs` with live status polling; once it completes, confirm the affected files actually moved to Drive's Trash (not permanently deleted) and that the Execution Timeline shows each step's result and verification status; try "Start rollback" from the plan's detail page and confirm the files come back out of Trash; separately, try rejecting a pending approval and confirm the plan is not touched at all.

## 8. Known limitations / follow-ups

- Same `packages/types` manual-sync caveat as every prior phase (ADR-012), now also covering `execution.ts`.
- **Only 3 of 11 recommendation rules are executable this phase** — every security/collaboration/productivity/knowledge-optimization finding remains view-only, by explicit design (ADR-020), not an oversight. `MOVE_FILE`/`MOVE_FOLDER`/`RENAME`/`UPDATE_METADATA` are implemented but unreachable from any current rule.
- **`ExecutionPlan.rollback_available` is per-plan, not per-step** — safe today because every supported action (Drive Trash) is uniformly reversible; will need to become per-step the day a genuinely irreversible action type is added.
- **Approval is single-decision-terminal** — no re-opening a rejected/changes-requested approval; a founder trying again needs a fresh plan. "Multi-step approvals" is explicitly deferred, per the phase spec's own future-readiness note.
- **No autonomous or recurring execution** — every job starts from one human's decision; scheduling/recurrence is explicitly Phase 9's content, not started here.
- **Rate limiting on execution/approval endpoints was not implemented this phase** — the spec's Security Requirements name it explicitly; the existing `app/presentation/dependencies/rate_limit.py` from an earlier phase was not extended to cover the three new routers. Flagged as a real gap, not a design choice.
- **No Docker/infrastructure worker-scaling config or monitoring metrics were added this phase** — the spec's Infrastructure Deliverables ask for both (pending-approvals count, successful/failed execution counts, rollback success rate, average execution time); this phase shipped the functional execution engine and left observability/scaling config for a follow-up pass.
- **`ExecutionStep.target_file_id` is a raw UUID in the API response**, same limitation Phase 7 already logged for `Recommendation.affected_file_ids` — the Plan Viewer links to `/files/$fileId` using the bare ID as visible link text.
- Route components remain outside the automated test suite by consistent design choice (see §7) — standing item in the CTO Dashboard's Technical Debt.
- Phase roadmap numbering/filename mismatch (this phase's content lives inside `PHASE_08_SECURITY_RELEASE.md`) — left unresolved at the founder's standing instruction, noted in the CTO Dashboard.

## 9. Recommendation for Phase 9

Phase 9's content (per the roadmap revision already visible inside these phase documents) is autonomous/recurring workflows — this phase deliberately built nothing in that direction, so Phase 9 starts from a clean boundary: every execution today requires a synchronous human `approve` click, and `ExecutionJob`/`ExecutionService` already have a complete, tested forward/rollback lifecycle a scheduler could trigger without redesigning the execution engine itself — the open question is what creates an `ExecutionPlan` and its `ApprovalRequest` on a recurring basis (a saved "always auto-approve this exact rule below this risk threshold" preference the founder configures once, versus a fully autonomous no-human-in-the-loop path the Core Philosophy's "no shortcuts" principle would need an explicit, deliberate exception for). The narrow 3-of-11 executable-rule allowlist is also a natural next-priority list: closing the gap for a few more of the eight currently view-only rules (most plausibly the other storage-optimization-adjacent ones) would make more of the Recommendation Engine's output actually actionable before investing in autonomy for a still-small action surface. Rate limiting and monitoring metrics, explicitly named in this phase's own spec but not completed, should be picked up either at the start of Phase 9 or as a small dedicated pass before it, since a recurring/autonomous execution surface makes both considerably more important than they were for a purely human-triggered one.
