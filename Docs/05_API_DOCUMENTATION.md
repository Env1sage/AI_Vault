# 05 — API Documentation

Status: **Reference document**, introduced in Phase 10. This is a navigable index of the REST API; the executable, always-current source of truth is the live OpenAPI schema at `/v1/openapi.json` and the Swagger UI at `/v1/docs` (any running backend instance). Request/response field-level detail lives there — this document explains conventions and gives you the map.

---

## 1. Conventions

- **Base path:** every product endpoint is under `/v1`. `/health/live`, `/health/ready`, and `/metrics` are operational endpoints outside `/v1` (Handbook §23, ADR-022) — not versioned, not part of the product API contract.
- **Auth:** a short-lived JWT access token in the `Authorization: Bearer <token>` header, obtained via `POST /v1/auth/login` and refreshed via a rotating `httpOnly` cookie (`POST /v1/auth/refresh`) — see ADR-013. Every endpoint except `POST /v1/auth/login`, `POST /v1/auth/refresh`, and the two health/metrics endpoints requires a valid access token.
- **RBAC:** three roles — `owner`, `admin`, `member`. Every mutating endpoint that can affect connected storage, workflows, or organization settings requires `owner` or `admin`; read endpoints are scoped to the caller's own organization only (`get_current_user`'s `organization_id`, never a client-supplied value).
- **Error shape:** every error response is `{"error": {"code": "...", "message": "...", "details": {...}}}` (`app/core/error_handlers.py`) — `code` is a stable machine-readable string (e.g. `not_found`, `validation_error`, `forbidden`), `message` is human-readable, `details` is endpoint-specific context (e.g. field-level validation errors).
- **Pagination:** most list endpoints return the full result set (organization-scoped, expected to stay small); `/v1/connectors/{id}/files` is the one paginated exception (`limit`/`offset` query params) since a file inventory can be large. See the [Release Readiness Report](phases/PHASE_10_COMPLETION_REPORT.md)'s Known Issues for the plan to extend this.
- **Rate limiting:** applied to auth endpoints, every job-starting endpoint (scan/enrichment/embedding/recommendation-refresh/workflow-trigger), every AI-Gateway-backed endpoint (search/conversations), the OAuth connector handshake, and the approval-decision endpoints (Phase 10, ADR-022). A `429` response uses the same error shape with `code: "rate_limit_exceeded"`.
- **Request IDs:** every response carries an `X-Request-Id` header (echoed from the request if the client sent one, generated otherwise) — the same ID appears in that request's structured log line and, if it triggered a background job, in every worker log line for that job too (`vault_request_id` correlation, ADR-022).

## 2. Endpoint index (by domain)

### Version & health
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health/live` | none | liveness — no dependency checks |
| GET | `/health/ready` | none | readiness — checks Postgres + Redis |
| GET | `/metrics` | none¹ | Prometheus scrape target |
| GET | `/v1/version` | none | build/version info |

¹ No application-layer auth — restrict at the network layer in production (Deployment Handbook §2).

### Auth & identity (Phase 2, ADR-013)
| Method | Path |
|---|---|
| POST | `/v1/auth/login` |
| POST | `/v1/auth/refresh` |
| POST | `/v1/auth/logout` |
| GET | `/v1/users/me` |
| GET | `/v1/organizations/current` |
| PATCH | `/v1/organizations/current` |

### Connector Platform (Phase 3, ADR-014)
| Method | Path |
|---|---|
| GET | `/v1/connectors` |
| POST | `/v1/connectors/google/connect` |
| POST | `/v1/connectors/google/callback` |
| GET | `/v1/connectors/{connector_id}/status` |
| POST | `/v1/connectors/{connector_id}/verify` |
| POST | `/v1/connectors/{connector_id}/disconnect` |

### Storage Scanner (Phase 4, ADR-015/016)
| Method | Path |
|---|---|
| POST | `/v1/connectors/{connector_id}/scans` |
| GET | `/v1/connectors/{connector_id}/scans` |
| GET | `/v1/scans/{scan_job_id}` |
| POST | `/v1/scans/{scan_job_id}/cancel` |

### Knowledge Engine (Phase 5, ADR-017)
| Method | Path |
|---|---|
| POST | `/v1/connectors/{connector_id}/enrichment` |
| GET | `/v1/connectors/{connector_id}/enrichment` |
| GET | `/v1/enrichment/{enrichment_job_id}` |
| POST | `/v1/enrichment/{enrichment_job_id}/cancel` |
| GET | `/v1/connectors/{connector_id}/files` (paginated) |
| GET | `/v1/files/{file_id}` |

### AI Intelligence Engine (Phase 6, ADR-018)
| Method | Path |
|---|---|
| POST | `/v1/connectors/{connector_id}/embedding` |
| GET | `/v1/connectors/{connector_id}/embedding` |
| GET | `/v1/embedding/{embedding_job_id}` |
| POST | `/v1/embedding/{embedding_job_id}/cancel` |
| POST | `/v1/search` |
| GET | `/v1/conversations` |
| GET | `/v1/conversations/{conversation_id}` |
| POST | `/v1/conversations` |
| POST | `/v1/conversations/{conversation_id}/messages` |

### Founder Command Center & Recommendation Engine (Phase 7, ADR-019)
| Method | Path |
|---|---|
| GET | `/v1/dashboard` (cached 30s per-org, ADR-022) |
| GET | `/v1/recommendations` |
| POST | `/v1/recommendations/refresh` |
| GET | `/v1/recommendations/{recommendation_id}` |

### Execution Engine & Approval System (Phase 8, ADR-020)
| Method | Path |
|---|---|
| POST | `/v1/execution-plans` |
| GET | `/v1/execution-plans` |
| GET | `/v1/execution-plans/{execution_plan_id}` |
| POST | `/v1/execution-plans/{execution_plan_id}/rollback` |
| GET | `/v1/approvals` |
| GET | `/v1/approvals/{approval_request_id}` |
| POST | `/v1/approvals/{approval_request_id}/decide` |
| POST | `/v1/approvals/bulk-decide` |
| GET | `/v1/execution-jobs` |
| GET | `/v1/execution-jobs/{execution_job_id}` |
| POST | `/v1/execution-jobs/{execution_job_id}/cancel` |
| POST | `/v1/execution-jobs/{execution_job_id}/pause` |
| POST | `/v1/execution-jobs/{execution_job_id}/resume` |

### Automation Engine (Phase 9, ADR-021)
| Method | Path |
|---|---|
| POST | `/v1/workflows` |
| GET | `/v1/workflows` |
| GET | `/v1/workflows/{workflow_id}` |
| GET | `/v1/workflows/{workflow_id}/versions` |
| POST | `/v1/workflows/{workflow_id}/draft` |
| PUT | `/v1/workflows/{workflow_id}/versions/{workflow_version_id}/nodes` |
| POST | `/v1/workflows/{workflow_id}/publish` |
| POST | `/v1/workflows/{workflow_id}/versions/{workflow_version_id}/rollback` |
| POST | `/v1/workflows/{workflow_id}/status` |
| POST | `/v1/workflows/{workflow_id}/clone` |
| POST | `/v1/workflows/{workflow_id}/triggers` |
| GET | `/v1/workflows/{workflow_id}/triggers` |
| POST | `/v1/workflows/{workflow_id}/triggers/{workflow_trigger_id}/enabled` |
| POST | `/v1/workflows/{workflow_id}/executions` |
| GET | `/v1/workflows/{workflow_id}/executions` |
| GET | `/v1/workflow-executions` |
| GET | `/v1/workflow-executions/{workflow_execution_id}` |
| POST | `/v1/workflow-executions/{workflow_execution_id}/cancel` |
| POST | `/v1/workflow-executions/{workflow_execution_id}/pause` |
| POST | `/v1/workflow-executions/{workflow_execution_id}/resume` |
| POST | `/v1/workflow-policies` |
| GET | `/v1/workflow-policies` |
| GET | `/v1/workflow-policies/{workflow_policy_id}` |
| GET | `/v1/workflow-policies/by-key/{policy_key}/versions` |
| POST | `/v1/workflow-policies/{workflow_policy_id}/publish` |
| POST | `/v1/workflow-policies/{workflow_policy_id}/archive` |
| GET | `/v1/notifications` |
| GET | `/v1/automation-templates` |
| POST | `/v1/automation-templates/{automation_template_id}/apply` |

**81 endpoints total** — 78 under `/v1`, plus 3 operational endpoints outside it (`/health/live`, `/health/ready`, `/metrics`).

## 3. Explore it live

```bash
docker compose -f infrastructure/docker/docker-compose.yml up
open http://localhost:8000/v1/docs
```

Swagger UI gives you the full request/response schema for every endpoint above, "Try it out" execution against your local stack, and the raw `/v1/openapi.json` if you want to generate a client SDK.
