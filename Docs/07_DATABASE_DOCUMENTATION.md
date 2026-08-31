# 07 — Database Documentation

Status: **Reference document**, introduced in Phase 10. PostgreSQL, one schema, one Alembic migration history (`apps/backend/alembic/`, shared by both apps — there is no separate worker schema). Every number below was queried directly against a real local database at migration head (`0009`, current as of Phase 10 — this phase added no schema changes of its own), not estimated.

---

## 1. At a glance

- **53 tables**, **162 indexes**, 9 migrations (`0001` → `0009`), one per phase from Phase 2 onward (Phase 1 had no schema).
- Every table with an `organization_id` column has it indexed — multi-tenancy was designed in from Phase 1 (Handbook §13), not retrofitted.
- Every table is append-only or soft-status-transitioned in practice — no phase has ever shipped a hard `DELETE` of business data; `AuditLog`/`ExecutionAudit`/`RecommendationEvent`/etc. are insert-only by construction (no repository method exists to update or delete a row).

## 2. Tables by phase

| Phase | Tables |
|---|---|
| 2 — Auth | `organizations`, `roles`, `users`, `refresh_tokens` |
| 3 — Connector Platform | `storage_connectors`, `connector_credentials` |
| 4 — Storage Scanner | `storage_sources`, `folders`, `files`, `scan_jobs`, `scan_progress`, `scan_events` |
| 5 — Knowledge Engine | `file_classifications`, `file_extractions`, `file_metadata`, `knowledge_attributes`, `file_relationships`, `enrichment_jobs`, `enrichment_progress`, `enrichment_events` |
| 6 — AI Intelligence Engine | `embeddings`, `embedding_jobs`, `embedding_progress`, `embedding_events`, `search_sessions`, `conversations`, `conversation_messages`, `citations` |
| 7 — Recommendation Engine | `recommendations`, `recommendation_jobs`, `recommendation_events`, `insight_records`, `dashboard_snapshots` |
| 8 — Execution Engine | `execution_plans`, `execution_steps`, `execution_jobs`, `execution_results`, `rollback_records`, `execution_audits`, `approval_requests`, `approval_decisions` |
| 9 — Automation Engine | `workflows`, `workflow_versions`, `workflow_nodes`, `workflow_triggers`, `scheduler_jobs`, `workflow_executions`, `workflow_node_executions`, `workflow_policies`, `notifications`, `automation_templates` |
| (Alembic bookkeeping) | `alembic_version` |

## 3. Key relationships

```text
organizations 1──* users ──* refresh_tokens
organizations 1──* storage_connectors 1──1 connector_credentials
storage_connectors 1──* storage_sources 1──* folders / files
files 1──1 file_classifications / file_extractions / file_metadata / knowledge_attributes
files *──* files (via file_relationships — sequential versions, duplicate candidates, shared ownership)
files 1──* embeddings
organizations 1──* recommendations (aggregate, natural-key-upserted — one active row per rule+scope, ADR-019)
recommendations 1──* execution_plans 1──* execution_steps
execution_plans 1──* approval_requests 1──1 approval_decisions
approval_decisions: exactly one of {decider_user_id, decided_by_policy_id} (ADR-021)
approval_requests: at least one of {execution_plan_id, workflow_node_execution_id} (ADR-021)
organizations 1──* workflows 1──* workflow_versions 1──* workflow_nodes
workflows 1──* workflow_triggers 1──1 scheduler_jobs (scheduled triggers only)
workflow_versions 1──* workflow_executions 1──* workflow_node_executions
```

The two `approval_*` CHECK constraints above are the schema-level enforcement of ADR-021's central claim ("automation never bypasses the Approval System") — a policy-driven auto-execution and a human's manual decision produce structurally identical rows, distinguished only by which of `decider_user_id`/`decided_by_policy_id` is populated.

## 4. Versioning/natural-key patterns

Three tables use the same "at most one active row per natural key, full history retained" pattern rather than in-place updates (first established for `Recommendation` in ADR-019, reused twice more in ADR-021):

- **`recommendations`** — one active row per `(organization_id, rule_name, scope)`; a rule that stops firing marks its prior row `RESOLVED`, never deletes it.
- **`workflow_versions`** — one `PUBLISHED` row per `workflow_id`; publishing a new version supersedes the prior one; "rollback" republishes an old `SUPERSEDED` version rather than creating a new row.
- **`workflow_policies`** — one `PUBLISHED` row per `policy_key`; every edit is a brand-new versioned row; publishing archives whatever was previously published.

## 5. Migration history

| Migration | Phase | Adds |
|---|---|---|
| `0001_enable_pgcrypto` | 2 | `pgcrypto` extension (UUID generation) |
| `0002_identity_tables` | 2 | `organizations`, `roles`, `users`, `refresh_tokens` |
| `0003_storage_connectors` | 3 | `storage_connectors`, `connector_credentials` |
| `0004_scanner_tables` | 4 | `storage_sources`, `folders`, `files`, `scan_*` |
| `0005_knowledge_engine_tables` | 5 | classification/extraction/metadata/knowledge/relationship + `enrichment_*` |
| `0006_ai_intelligence_tables` | 6 | `embeddings`, `embedding_*`, `search_sessions`, `conversations`, `conversation_messages`, `citations` |
| `0007_recommendation_engine_tables` | 7 | `recommendations`, `recommendation_*`, `insight_records`, `dashboard_snapshots` |
| `0008_execution_engine_tables` | 8 | `execution_*`, `rollback_records`, `approval_*` |
| `0009_automation_engine_tables` | 9 | `workflow_*`, `scheduler_jobs`, `workflow_policies`, `notifications`, `automation_templates`; ALTERs `approval_requests`/`approval_decisions` for the policy-as-approver pattern |
| `0010_file_web_view_link` | 10 | ALTERs `files` — adds `web_view_link` |
| `0011_storage_intelligence_tables` | Storage Intelligence (ADR-023) | `storage_analysis_*`, `duplicate_groups`, `duplicate_group_members` |
| `0012_execution_plan_duplicate_group_origin` | Storage Intelligence (ADR-023) | ALTERs `execution_plans` — adds `duplicate_group_id` origin |
| `0013_execution_plan_ad_hoc_origin` | Storage Intelligence (ADR-023) | ALTERs `execution_plans`' origin check constraint for ad-hoc (file-list) plans |
| `0014_file_intelligence_tables` | AI File Intelligence | `file_intelligence`, `intelligence_jobs`, `intelligence_progress`, `intelligence_events` |
| `0015_conversation_message_tool_name` | AI Storage Assistant (ADR-024) | ALTERs `conversation_messages` — adds `tool_name` |

Every migration has a full, tested `downgrade()` — used in practice during development at least once per phase from Phase 4 onward (the established "downgrade → fix → reapply" iteration pattern logged in this project's ADRs). No migration has ever been edited after being applied in a shared/CI environment; `0008`'s two-line whitespace fix in Phase 10 (wrapping overlong `op.create_index` calls) is the one cosmetic exception, made before this phase's own CI run, not after any real deployment.

## 6. Backup & restore

See the [Disaster Recovery Guide](10_DISASTER_RECOVERY_GUIDE.md) for the full procedure and a real drill's results (all 53 tables verified byte-for-byte row-count-identical between a live backup and a restored copy, Phase 10).

## 7. Indexing strategy

Every column used as a query filter in the current codebase is indexed — `organization_id` (every multi-tenant table), `status` (every job/plan/request table), foreign keys used in `list_for_*`-style repository methods (`connector_id`, `workflow_id`, `recommendation_id`, etc.). A Phase 10 audit (`information_schema`/`pg_index` cross-query) found 26 columns without an index — all of them attribution-only foreign keys (`created_by_user_id`, `triggered_by_user_id`, `decided_by_policy_id`, and similar "who did this" references) that no current query filters or joins on; adding indexes there would cost write throughput for no read benefit against today's actual access patterns, so none were added. Revisit if a future feature needs to query "everything user X triggered."
