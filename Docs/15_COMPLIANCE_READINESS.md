# 15 — Compliance Readiness

Status: **Living document**, introduced in Phase 10 per the phase spec's own framing: "implementation can be staged later, but architectural readiness should exist now." This is an honest inventory of where the architecture already supports common compliance requirements and where real implementation work remains — not a certification, and not legal advice. Engage qualified counsel and, where relevant, a formal auditor before making any compliance claim to a customer.

---

## 1. GDPR (or equivalent data-protection regulation)

| Requirement | Architectural readiness | Gap |
|---|---|---|
| Data minimization | This platform stores metadata, classification, and vector embeddings — never a copy of file *content* itself (content is extracted transiently for classification/embedding, then discarded, not persisted) | None identified |
| Right to erasure | Every record is organization-scoped with real foreign keys — a full "delete this organization's data" cascade is a schema-level possibility (`ON DELETE CASCADE` already used throughout) | No user-facing "delete my organization" endpoint exists yet — a real, if straightforward, feature to build |
| Right to access / data portability | Every organization's data is queryable via the existing API | No consolidated "export everything for this organization" endpoint yet |
| Data Processing Agreement readiness | Sub-processors are enumerable (Google, and eventually a real LLM provider) since every external call is gated through named boundaries (Connector Platform, AI Gateway) | Requires a real DPA document, a legal/business artifact this document doesn't produce |
| Breach notification | Audit logging (`AuditLog`, `ExecutionAudit`) provides a forensic trail of every mutating action; Sentry (once configured) provides real-time error visibility | No formalized incident-response/notification procedure yet — a process document, not code |

## 2. SOC 2 (readiness, not certification)

| Trust Service Criteria | Readiness |
|---|---|
| Security | RBAC, org isolation, encryption at rest/in transit, rate limiting, dependency scanning, security headers — all in place (see [Security Guide](08_SECURITY_GUIDE.md)) |
| Availability | Health checks, graceful shutdown, Multi-AZ database/cache in production, automated backup/restore (drilled — [DR Guide](10_DISASTER_RECOVERY_GUIDE.md)), CloudWatch alarms | No formal uptime SLA or incident postmortem process defined yet |
| Processing integrity | Every mutating action is plan-then-approve-then-execute with a full audit trail; execution steps are individually verified post-mutation | — |
| Confidentiality | Org isolation enforced at every query; secrets in Secrets Manager, never in code/images | — |
| Privacy | See GDPR section above | Same gaps |

A SOC 2 Type II audit specifically requires demonstrating these controls operated effectively *over a period of time* in a real production environment — not achievable until this platform has actually been running in production, regardless of code readiness.

## 3. ISO 27001

Overlaps heavily with SOC 2's Security criterion above. The main additional expectation is a formal Information Security Management System (ISMS) — documented risk assessments, a management review cadence, a defined scope statement — which is an organizational process, not something this codebase can satisfy on its own. The technical controls this platform already has (access control, cryptography, logging, change management via CI/CD and code review) map to specific ISO 27001 Annex A controls and would form the evidence base for such an ISMS, once one exists.

## 4. Data retention

| Data | Current retention | Configurable? |
|---|---|---|
| Business records (files metadata, recommendations, executions, workflows) | Indefinite | No explicit retention policy or auto-purge exists yet |
| Audit logs | Indefinite, insert-only | Same |
| Database backups | 14 local / 90-365 days in S3 (environment-dependent) | Yes — `BACKUP_RETENTION_COUNT`, Terraform `backup_retention_days` |
| Refresh tokens | Expire per `REFRESH_TOKEN_EXPIRE_DAYS` (30 days default), old ones marked replaced, never silently kept alive | Yes |

A real data-retention *policy* (how long to keep a resolved recommendation, a completed execution's audit trail, a disconnected connector's historical scan data) is a business decision this document doesn't make — the schema supports adding a purge job once that decision exists (every table has `created_at`/`updated_at`, making age-based filtering straightforward).

## 5. Data deletion

Beyond GDPR's right-to-erasure (§1): this platform's core promise is that it *never permanently deletes the customer's own files* — every execution action uses Google Drive's own Trash, always recoverable by the customer independent of this platform. This is a product principle (Handbook, Core Philosophy) as much as a compliance posture.

## 6. Audit requirements

Already substantially built: `AuditLog` (connector connect/disconnect, verification), `ExecutionAudit` (every execution step, before and after state), approval decisions (who/what decided, when, with what reasoning), workflow execution history (every node's outcome). All insert-only by construction (no repository exposes update/delete — [Security Guide](08_SECURITY_GUIDE.md) §10). **Gap:** no database-role-level `REVOKE UPDATE, DELETE` yet — the guarantee currently rests on application code never calling those operations, not on the database refusing to allow them even to a compromised application credential.

## 7. Summary: staged implementation plan

1. **Now (architectural readiness):** the items marked "readiness" above — already true, verified by this document's audit of the actual code.
2. **Before any compliance claim to a customer:** legal review of a real DPA/privacy policy; a formal incident-response procedure; database-role-level audit-table protection.
3. **Before certification (SOC 2 Type II / ISO 27001):** a real production environment running long enough to demonstrate controls operating over time; a formal ISMS; an external auditor engagement.

None of the above blocks Version 1.0's release for early customers who don't yet require formal certification — it is the honest map of what remains before this platform can support a customer who does.
