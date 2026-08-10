# 11 — Monitoring Guide

Status: **Living document**, introduced in Phase 10 (ADR-022). What's instrumented, where to look at it, and how to add more.

---

## 1. Stack

| Layer | Tool | Status |
|---|---|---|
| Metrics | Prometheus + Grafana | Always on, real data |
| Tracing | OpenTelemetry | Off by default — set `OTEL_EXPORTER_OTLP_ENDPOINT` |
| Error tracking | Sentry | Off by default — set `SENTRY_DSN` |
| Logs | Structured JSON → stdout → CloudWatch (production) / `docker compose logs` (local) | Always on |

Tracing and error tracking follow the same "stub until configured" pattern this codebase already uses for the LLM provider (ADR-018) and email (ADR-021) — leaving them unset costs nothing and breaks nothing; every instrumentation call in the code is unconditional (`FastAPIInstrumentor`, `CeleryInstrumentor`, etc.) and becomes a real no-op without a configured endpoint/DSN.

## 2. Running it locally

```bash
docker compose \
  -f infrastructure/docker/docker-compose.yml \
  -f infrastructure/docker/docker-compose.monitoring.yml \
  up
```

- Grafana: http://localhost:3001 (`admin`/`admin` — change on first login). Two dashboards auto-provisioned: **API Overview** and **Worker & Automation Overview**.
- Prometheus: http://localhost:9090.
- Backend metrics directly: http://localhost:8000/metrics.
- Worker metrics: http://localhost:9101 (served by the dedicated `worker-metrics` sidecar — see §4).

## 3. What's measured

| Metric | Type | Labels | What it tells you |
|---|---|---|---|
| `vault_http_requests_total` | Counter | `method`, `path`, `status_code` | Request volume, error rate by route |
| `vault_http_request_duration_seconds` | Histogram | `method`, `path` | Latency percentiles (the Grafana dashboards compute p50/p95/p99) |
| `vault_celery_tasks_total` | Counter | `task_name`, `status` | Job throughput and failure rate, per task type |
| `vault_celery_task_duration_seconds` | Histogram | `task_name` | How long each pipeline stage actually takes |
| `vault_queue_depth` | Gauge | `queue_name` | Backlog — is the worker fleet keeping up |
| `vault_ai_provider_latency_seconds` | Histogram | `provider`, `operation` | Embedding/completion call latency, instrumented at the `AIGateway` boundary itself so every caller gets it for free |
| `vault_workflow_executions_total` | Counter | `status` | Automation health — completed vs. failed vs. cancelled workflow runs |

`path` is always the route *template* (`/v1/files/{file_id}`), never a resolved path containing a real ID — using a real UUID as a label value would be an unbounded-cardinality mistake that degrades Prometheus itself, not just this app's own dashboards.

## 4. The worker metrics caveat (read before scaling workers past one replica)

Celery's default `prefork` pool is multi-process — each task executes in a forked child, so a metrics registry living inside any single process only ever reflects that process's share of the traffic. The fix, `PROMETHEUS_MULTIPROC_DIR`, is wired up (every `worker` container and the dedicated `worker-metrics` sidecar share a volume/directory; `worker-metrics` is a separate always-on process — `python -m worker.metrics_server` — that merges every child's files on each scrape). This is the officially-documented `prometheus_client` pattern for exactly this situation, verified correct by Docker Compose's config-merge output (`docker compose ... config`) during Phase 10 development — but **has not been exercised against a real multi-replica worker fleet actually processing tasks**, since no Docker daemon was available in that development environment. Before relying on worker metrics in production: deploy with 2+ worker replicas, generate real task traffic, and confirm the Grafana "Worker & Automation Overview" dashboard shows combined (not single-replica) numbers.

## 5. Alerting

CloudWatch alarms (`infrastructure/terraform/modules/monitoring`) cover infrastructure-layer signals — backend CPU, ALB 5xx count, RDS free storage, RDS connection count — wired to an SNS topic with an email subscription (`pager_email` Terraform variable). These are complementary to, not a replacement for, the Prometheus/Grafana application-layer metrics above; CloudWatch alarms fire even if Grafana itself is down.

**Not yet wired:** Grafana-native alerting rules on the application metrics themselves (e.g., "page if the workflow failure rate exceeds 10% over 15 minutes") — the dashboards exist and are correct, but nothing currently pages off of them directly. A natural Phase 11 item.

## 6. Correlation IDs — tracing one request across both apps

Every HTTP response carries `X-Request-Id`. If that request enqueued a Celery task, the same ID travels with it as a `vault_request_id` custom header (not `correlation_id` — that name collides with Celery's own reserved AMQP property, see ADR-022) and appears as `request_id` in every worker log line for that task's execution. A task with no originating HTTP request (a scheduler-fired trigger, a chained job) falls back to its own Celery task ID instead — every log line is always attributable to *something*.

```bash
# find everything that happened because of one specific API call
grep '"request_id": "<the-id-from-X-Request-Id>"' backend.log worker.log
```

## 7. Adding a new metric

1. Define it once in `packages/shared/vault_shared/metrics.py` (a module-level `Counter`/`Histogram`/`Gauge`) — both apps import from here so the same metric name means the same thing everywhere.
2. Add a small `record_*`/`set_*` helper function next to it, rather than calling `.labels(...).inc()` directly at every call site.
3. Call the helper from wherever the event actually happens.
4. Add a panel to the relevant Grafana dashboard JSON (`infrastructure/monitoring/grafana/dashboards/`) if it's worth looking at regularly.

## 8. Business metrics named in the phase spec but not yet built

"Automation savings" (time/money saved by automated vs. manual execution) is explicitly named as a future metric in Phase 9's own spec — no baseline/comparison logic exists yet to compute it. Tracked as a known limitation, not silently dropped.
