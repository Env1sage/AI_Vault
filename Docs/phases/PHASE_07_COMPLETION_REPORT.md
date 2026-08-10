# Phase 7 — Completion Report

**Phase:** [`PHASE_07_EXECUTION_ENGINE.md`](PHASE_07_EXECUTION_ENGINE.md) — Founder Command Center & Recommendation Engine (filename is stale — see Technical Debt in the CTO Dashboard; the document's own in-text roadmap revision renames its content "Founder Command Center & Recommendation Engine," not Execution Engine)
**Status:** Implemented by Claude. Awaiting founder manual test and CTO review (Engineering Handbook §4 lifecycle) before being marked complete in [`01_PROJECT_MASTER.md`](../01_PROJECT_MASTER.md).
**Date:** 2026-08-03

---

## 1. Read this first — the architectural decisions this phase required

**ADR-019 — Recommendation Engine design.** The phase spec asks for a Recommendation Engine spanning five categories (storage, knowledge, security, collaboration, productivity) that combines "metadata, knowledge graph, semantic search, AI reasoning (only when necessary), deterministic rules," an explainable/configurable Prioritization Engine, and a Founder Command Center dashboard with historical trend data — explicitly forbidding any recommendation from executing an action. Three concrete design questions had no spec answer: (1) `RecommendationJob` is the first job type in this codebase scoped to an *organization* rather than a connector, since recommendations and the dashboard reason about an org's storage as a whole ("Connected storage providers" is one of the Organization Overview's own display fields); (2) each rule produces at most one aggregate recommendation per organization (natural key `(organization_id, rule_name)`), never one row per affected file — the phase spec's own worked example ("18% of your storage is occupied by duplicate marketing assets") is explicitly aggregate, not per-item; (3) "AI reasoning (only when necessary)" is honored by making zero `AIGateway.complete()` calls this phase — with the completion provider still ADR-018's explicit stub, calling it per-rule would add latency for no real reasoning, so `RecommendationRule`/`InsightGenerator` are `Protocol`s a future AI-reasoning rule can implement without a redesign. See [ADR-019](../03_ARCHITECTURE_DECISIONS.md#adr-019-recommendation-engine-phase-7--organization-scoped-jobs-aggregate-not-per-item-recommendations-and-a-100-deterministic-rule-set) for full reasoning and alternatives considered.

## 2. Repository changes

```text
packages/shared/vault_shared/
  db/models/
    recommendation_job.py        NEW — RecommendationJob (+ RecommendationJobStatus, RecommendationTrigger),
                                 organization-scoped (not connector-scoped), no cancel_requested column
    recommendation_event.py      NEW — RecommendationEvent, mirrors EmbeddingEvent (append-only)
    recommendation.py            NEW — Recommendation (+ RecommendationCategory, RecommendationRiskLevel,
                                 RecommendationStatus), unique (organization_id, rule_name)
    insight_record.py            NEW — InsightRecord, append-only informational observations
    dashboard_snapshot.py        NEW — DashboardSnapshot, append-only point-in-time org metrics
  db/repositories/
    recommendation_job_repository.py, recommendation_event_repository.py,
    recommendation_repository.py (upsert/resolve_stale/list/get), insight_record_repository.py,
    dashboard_snapshot_repository.py                                     NEW — one per model above
    file_repository.py            + list_recently_modified_for_organization, list_for_organization_with_details
                                  (File+FileMetadata+FileClassification+workspace_domain, one org-scoped join)
    folder_repository.py          + count_for_organization
    file_relationship_repository.py + list_for_organization
    knowledge_attribute_repository.py + list_department_values_for_files (bounded batch lookup)

apps/worker/worker/recommendation/
  context.py                    NEW — FileRow, RuleContext, RuleResult, InsightResult dataclasses
  formatting.py                 NEW — human_bytes() — dependency-free byte formatter for impact prose
  priority.py                   NEW — score_priority(): explainable weighted-sum prioritization
  rules.py                      NEW — RecommendationRule protocol + 11 rules: DuplicateFilesRule,
                                 ArchiveCandidateRule, LargeUnusedFilesRule (storage); PendingEnrichmentRule,
                                 LowRelationshipCoverageRule (knowledge); PubliclySharedFilesRule,
                                 OrphanedOwnershipRule, SensitiveSharedContentRule (security);
                                 InactiveSharedFilesRule, OwnershipConcentrationRule (collaboration);
                                 LowConfidenceClassificationReviewRule (productivity)
  insights.py                   NEW — InsightGenerator protocol + 2 generators: HighConnectivityDocumentsInsight,
                                 FileSizeAnomalyInsight
  recommendation_service.py     NEW — RecommendationService: run/_generate — org-scoped data pull, evaluates
                                 every rule/insight, persists recomputable recommendations + one snapshot

apps/worker/worker/tasks/
  recommendation.py             NEW — worker.recommendation.run Celery task, no retry policy
  embedding.py                  + _enqueue_recommendation_if_embedding_completed (resolves connector →
                                 organization, auto-chains after a completed embedding job)
  celery_app.py                 + "worker.tasks.recommendation" in the include list

apps/backend/app/
  application/
    dashboard_service.py         NEW — DashboardService: get_overview (connectors, latest/historical
                                  snapshots, recent insights, recent activity, latest job statuses per stage)
    recommendation_service.py    NEW — RecommendationService: list_for_organization/get_owned (role-gated
                                  SECURITY-category filtering, audited detail views), trigger_refresh
  infrastructure/queue/
    recommendation_producer.py    NEW — enqueue_recommendation_job, same task-name-string pattern as prior stages
  presentation/
    api/v1/dashboard.py            NEW — GET /dashboard
    api/v1/recommendations.py      NEW — GET /recommendations, GET /recommendations/{id},
                                  POST /recommendations/refresh
    api/v1/schemas.py              + DashboardSnapshotResponse, InsightRecordResponse, DashboardResponse,
                                  RecommendationResponse, RecommendationListResponse, RecommendationJobResponse
    api/v1/router.py               + dashboard_router, recommendations_router
    dependencies/services.py       + get_dashboard_service, get_recommendation_service
  alembic/versions/0007_recommendation_engine_tables.py   recommendation_jobs, recommendation_events,
                                  recommendations, insight_records, dashboard_snapshots (full downgrade() included)

packages/types/src/dashboard.ts, recommendations.ts   NEW — Dashboard, DashboardSnapshot, InsightRecord,
                                  Recommendation(Category/RiskLevel/Status/ListResponse), RecommendationJob
packages/types/src/index.ts       + re-exports

apps/frontend/src/
  routes/dashboard.tsx            REBUILT — Organization Overview stat tiles, Storage Health (+ inline SVG
                                  trend sparkline, no charting dependency), Knowledge Health, AI Insights feed,
                                  Recommendation Center preview (top 5 by priority + "Refresh" action, owner/
                                  admin only), Recent Activity feed; existing "Backend connectivity" diagnostic
                                  section kept, moved to the bottom
  routes/recommendations.tsx      NEW — category/status filters, search box, priority-sorted list
  routes/recommendations.$recommendationId.tsx   NEW — full detail view (confidence, impact, risk,
                                  suggested action, affected files, departments, generated timestamp)
  lib/recommendation-style.ts (+ .test.ts)   categoryLabel/categoryColor/riskColor — pure, unit-tested
  lib/format-bytes.ts (+ .test.ts)   formatBytes — pure, unit-tested

tests/unit/backend/test_dashboard_router.py, test_recommendations_router.py         NEW — 3 + 9 tests
tests/integration/backend/test_dashboard_service_integration.py,
  test_recommendation_service_integration.py                                       NEW — 3 + 6 tests, real Postgres
tests/unit/worker/test_recommendation_rules.py, test_recommendation_priority.py,
  test_recommendation_insights.py                                                  NEW — 19 + 5 + 4 tests
tests/integration/worker/test_recommendation_service_integration.py                NEW — 4 tests, real Postgres
```

## 3. Database changes

Migration `0007_recommendation_engine_tables` (on top of Phase 6's `0006_ai_intelligence_tables`):

- **`recommendation_jobs`** — organization-scoped (not connector-scoped, the first job type that isn't). Plain status lifecycle (`pending`/`running`/`completed`/`failed`), no `cancel_requested` column and no companion progress table — a deliberate proportionality call (ADR-019), not an oversight: a recommendation run is a single fast deterministic pass with nothing to cancel mid-flight or report incremental progress on.
- **`recommendation_events`** — append-only operational trail, mirrors `embedding_events` exactly (same defensive `message[:1024]` truncation).
- **`recommendations`** — organization-scoped, unique on `(organization_id, rule_name)`. `affected_file_ids`/`related_departments` are plain JSONB arrays, not join tables. `status` transitions `active → resolved` (never deleted) when a rule stops firing on a later run. `requires_approval` defaults `true` on every row — unused this phase, present for Phase 8's Approval & Execution System to build on without a migration.
- **`insight_records`** — organization-scoped, append-only (no status/resolve lifecycle — an insight is a dated observation, not an open issue).
- **`dashboard_snapshots`** — organization-scoped, append-only, one row per `RecommendationJob` run. This *is* the trend-chart data source; no separate time-series store.

Verified via `alembic upgrade head --sql` (correct SQL) and applied for real against the founder's live local Postgres instance (`alembic upgrade head` succeeded, `0006 → 0007`).

## 4. API surface

```text
GET    /v1/dashboard                          (any authenticated org member)  → DashboardResponse
GET    /v1/recommendations                    (any authenticated org member)  → RecommendationListResponse
                                                (query: category, status [default "active"], search;
                                                 SECURITY-category rows excluded unless owner/admin)
GET    /v1/recommendations/{id}               (any authenticated org member)  → RecommendationResponse
                                                (403 Forbidden, not 404, if it's a SECURITY item and the
                                                 caller isn't owner/admin; every view is audit-logged)
POST   /v1/recommendations/refresh            (owner/admin)                    → RecommendationJobResponse (201)
```

`GET /v1/recommendations` defaults `status=active` so the Recommendation Center shows open issues by default, with `status=` (empty) or `status=resolved` available for history. Role gating for `SECURITY` is enforced in `RecommendationService`, not the router — the same service method a future internal caller would use inherits the restriction automatically.

## 5. Worker behavior

`RecommendationService.run(recommendation_job_id)`: loads the job, marks `RUNNING`, records a `recommendation_started` event, then in one pass pulls the organization's entire current state — every file with its metadata/classification/connector-workspace-domain (`FileRepository.list_for_organization_with_details`), every relationship edge (`FileRelationshipRepository.list_for_organization`), every embedded file id (`EmbeddingRepository.list_for_organization`, reused from Phase 6), and folder/connector counts. Below 5 files, rule evaluation is skipped entirely (ratio-based signals are meaningless noise at that scale) but a `DashboardSnapshot` is still recorded. Each of the 11 rules and 2 insight generators runs against this shared context; a rule/insight that throws is caught, logged, and recorded as a `rule_failed` event without stopping the others (mirroring every prior phase's per-item failure isolation, just applied per-rule instead of per-file). Every fired rule's result is priority-scored (`score_priority`, normalized against the run's own maximum `impact_value`) and upserted; every rule that *didn't* fire this run has its previous `ACTIVE` recommendation (if any) resolved via `RecommendationRepository.resolve_stale`. Finally one `DashboardSnapshot` is persisted with the run's aggregate counts, and the job is marked `COMPLETED` with `recommendations_active` set to the current active count.

`worker/tasks/embedding.py`'s `_enqueue_recommendation_if_embedding_completed` runs after every successful embedding job: it resolves the connector back to its organization (`StorageConnectorRepository.get_by_id`), then creates a `RecommendationJob` (`triggered_by=EMBEDDING_COMPLETED`) and calls `run_recommendation.delay(...)` directly — same plain in-process Celery call pattern as every prior stage's chain, but the first one that changes scope (connector event → organization-level job) partway through. Skipped if a recommendation job is already active for that organization, or if the embedding job didn't complete successfully.

## 6. Recommendation logic

Eleven deterministic rules, each an explicit, documented approximation of its phase-spec example where this platform's captured data is coarser than what the spec's prose implies:

- **Storage Optimization** — `duplicate_files` (reuses Phase 5's checksum-exact `duplicate_group_key`, aggregates into one "N groups, ~X GB reclaimable" recommendation); `archive_candidates` (no modification/view activity in 365+ days); `large_unused_files` (>100MB *and* no activity in 180+ days — both conditions required).
- **Knowledge Optimization** — `pending_enrichment` (files with no `FileMetadata` row at all — the pipeline backlog, literally the spec's own "Documents pending enrichment" example); `low_relationship_coverage` (fewer than 10% of enriched files participate in any discovered relationship edge).
- **Security** — `publicly_shared_files` (approximates "publicly shared" as `File.is_shared`, since Phase 3/4's scanner never captured Drive's actual permission granularity — link-shared vs. specific-people sharing are indistinguishable today, documented explicitly in the rule and the recommendation's own description text); `orphaned_ownership` (owner's email domain differs from the connector's workspace domain — a precise signal, not an approximation); `sensitive_shared_content` (classification document-type in `{Invoice, Contract}` *and* shared — a mime/keyword-based proxy for sensitivity, not a real content scan).
- **Collaboration** — `inactive_shared_files` (shared *and* stale — same activity signal as archive candidates, different framing/category); `ownership_concentration` (one owner holds ≥50% of an org's shared files, single-point-of-failure risk).
- **Productivity** — `low_confidence_classification_review` (classification confidence below 40% — ties directly to the spec's "Documents requiring review" example).

Two insight generators feed the dashboard's informational "AI Insights" section (no risk level, no suggested action, never resolved — see ADR-019 on why insights and recommendations are deliberately different persistence shapes): `high_connectivity_documents` (files with the most relationship edges — a proxy for "foundational" documents) and `file_size_anomaly` (a file more than 5x its document-type peer group's median size).

Prioritization (`worker/recommendation/priority.py`) is a plain weighted sum — `0.35×confidence + 0.35×risk_weight + 0.15×category_weight + 0.15×normalized_impact`, all named module-level constants, every input already visible on the recommendation itself.

## 7. Tests and what was actually verified in this environment

- **Backend:** 202 tests total (12 new — `/v1/dashboard` and `/v1/recommendations` routers via `TestClient` + `dependency_overrides`, same pattern as every prior router, including the 403-vs-404 distinction for hidden security items) + 9 new integration tests against real Postgres (`DashboardService` org isolation; `RecommendationService` role-based security filtering across both `list_for_organization` and `get_owned`, cross-org rejection, active-job conflict on manual refresh). `ruff`/`mypy` clean.
- **Worker:** 123 tests total (4 new integration tests against real Postgres: a duplicate-files recommendation actually persisting with the correct reclaimable-bytes math, a dashboard snapshot persisting with correct counts, **a recommendation correctly transitioning `ACTIVE → RESOLVED` across two runs** when its underlying condition is removed between them, and near-empty-organization rule-skipping; 28 new unit tests — 19 covering all 11 rules' fire/no-fire boundary conditions against in-memory `FileRow`/`RuleContext` fixtures — no DB — plus 4 for the 2 insight generators and 5 for the priority-scoring formula). `ruff`/`mypy` clean.
- **Frontend:** `tsc --noEmit`, `eslint .` clean on the rebuilt `/dashboard` and the new `/recommendations`/`/recommendations/$recommendationId` routes; 10 new vitest tests (`format-bytes`, `recommendation-style`) plus a full `vite build` confirming all three routes register correctly in the generated route tree and code-split into their own chunks. Same one pre-existing, unrelated vitest failure noted in the Phase 6 report (`google-sign-in-button.test.tsx`) — still not a regression from this phase.
- **Live, not just mocked.** Every layer of this phase was exercised end-to-end against the founder's real, already-scanned/enriched/embedded ~1,000-file Google Drive account: `RecommendationService.run()` executed directly against the real database produced **7 real recommendations** (a 7-file sensitive-shared-content flag, a 587-file archive-candidate list totaling ~15GB, a 37-file large-unused-files list, a 12-group/17-file duplicate-files finding, a 760-file publicly-shared flag, a 463-file inactive-shared-files flag, and a 103-file low-confidence-classification flag) and **2 real insights**, all with plausible, human-readable explanations; a second run against the same data confirmed idempotent upsert behavior (same 7 rows, no duplicates); `GET /v1/dashboard` and the full `/v1/recommendations` flow (list, category filter, detail, manual refresh) were hit via real HTTP with a minted JWT against a running `uvicorn` server and returned exactly the expected data, including the role-based security-category filtering (a member sees 5 of 7 recommendations, an owner sees all 7) and a live `AuditLog` row written on detail view.

**Concrete manual-test steps for the founder**, beyond Phase 1-6's checklist: with a connected Workspace connector and a completed embedding run, confirm a recommendation job auto-starts and completes quickly (visible via `latest_recommendation_status` on `/dashboard`) without any manual action; visit `/dashboard` and confirm the Organization Overview tiles, Storage Health trend sparkline, Knowledge Health percentage, AI Insights feed, and Recent Activity feed all show plausible numbers for the real account; click into the Recommendation Center preview and confirm at least one recommendation makes sense for what's actually in the account; visit `/recommendations`, filter by category, search by keyword, and confirm results update; open a recommendation's detail page and confirm the suggested action and affected-file count are sensible; as a `member`-role user, confirm no `security`-category recommendation appears in the list or is reachable directly; click "Refresh recommendations" as an owner/admin and confirm it completes and the dashboard reflects a fresh snapshot.

## 8. Known limitations / follow-ups

- Same `packages/types` manual-sync caveat as prior phases (ADR-012), now also covering `dashboard.ts`/`recommendations.ts`.
- **Security/sensitivity rules are documented approximations, not precise checks** — "publicly shared" is `File.is_shared` (no link-vs-specific-people distinction), "sensitive content" is classification document-type (no real content scan). Explicit in ADR-019, not an oversight — revisit if a future phase captures Drive's actual per-file ACL detail.
- **Zero real AI/LLM reasoning this phase** — every recommendation's explanation is a templated string built from the rule's own computed numbers, per ADR-019's "no `AIGateway` calls" decision (consistent with Phase 6's still-stubbed completion provider). `RecommendationRule`/`InsightGenerator` are ready for an AI-reasoning-based rule once a real provider is wired in.
- **`Recommendation.requires_approval` is unused** — set to `true` on every row, read by nothing yet. This is precisely the field Phase 8's Execution & Approval System is expected to build on.
- **`Recommendation.affected_file_ids` are raw UUIDs in the API response**, not enriched with file name/path — the frontend detail page links to `/files/$fileId` using the bare ID as visible link text. Functional, not polished; a future pass could have the backend join file summaries in.
- **The pre-existing mixed-embedding-model-version gap (ADR-018) is now also relevant here** — the relationship-coverage rule and connectivity insight both read `Embedding` rows the same brute-force way `SearchService` does, so a file embedded under a stale model version could skew both signals identically. Not solved this phase either.
- **No job-level retry or cooperative cancellation for `RecommendationJob`**, unlike every prior job type — a deliberate proportionality decision (ADR-019: no per-item external I/O, nothing to retry around or interrupt), not a gap to close reflexively. Revisit only if a future rule adds real per-item work that could fail or run long.
- Route components remain outside the automated test suite by consistent design choice (see §7) — standing item in the CTO Dashboard's Technical Debt.
- Phase roadmap numbering/filename mismatch (this phase's content lives inside `PHASE_07_EXECUTION_ENGINE.md`, whose own in-text roadmap revision names Phase 8 as the Execution & Approval System) — left unresolved at the founder's standing instruction, noted in the CTO Dashboard.

## 9. Recommendation for Phase 8

Every `Recommendation` already carries `requires_approval` (currently always `true`, always unread) and a `suggested_action` string — exactly the two fields an Approval & Execution System needs to build an approve/reject/execute workflow on, without a schema change. The `RecommendationRepository.upsert`/`resolve_stale` lifecycle already distinguishes "this is still a live issue" (`ACTIVE`) from "this got fixed" (`RESOLVED`) — Phase 8 should decide whether an *approved-and-executed* recommendation needs a third status, or whether execution should be tracked in a separate table referencing the recommendation (the latter keeps `Recommendation` itself execution-agnostic, consistent with this phase's explicit "no recommendation is executed" boundary). `suggested_action` today is human-readable prose, not a structured action descriptor (e.g. "delete these N files") — Phase 8 will likely need to add a structured, rule-specific action payload (which files, what operation) alongside the prose, since "read this sentence and go do it in Drive" doesn't give an execution engine anything machine-actionable to work from. The Recommendation Engine's own rule set is a natural first list of *what* Phase 8 should be able to execute (duplicate cleanup and archive candidates are the two most mechanically executable of the eleven; security/collaboration findings are more naturally "flag for human review" than "auto-execute," and should probably stay that way even once execution exists).
