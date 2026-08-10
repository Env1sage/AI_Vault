# 09 — Operations Runbook

Status: **Living document**, introduced in Phase 10. Day-2 operations — what to check when something looks wrong, and how to act on it. For deploying a new release, see the [Deployment Handbook](04_DEPLOYMENT_HANDBOOK.md). For a full outage/data-loss scenario, see the [Disaster Recovery Guide](10_DISASTER_RECOVERY_GUIDE.md).

---

## 1. First response: is it actually broken?

```bash
curl https://<your-domain>/health/live    # process is up
curl https://<your-domain>/health/ready   # process can reach Postgres + Redis
infrastructure/scripts/smoke_test.sh https://<your-domain>   # the 3-endpoint fast check
```

`/health/ready` returning `503` with `{"status": "degraded", "checks": {...}}` tells you *which* dependency is unreachable — check that dependency next, not the app.

## 2. Where the signal is

| Question | Where to look |
|---|---|
| Is the API slow / erroring? | Grafana → "API Overview" dashboard (request rate, p50/p95/p99 latency, 5xx ratio, slowest routes) — see [Monitoring Guide](11_MONITORING_GUIDE.md) |
| Is a background job stuck? | Grafana → "Worker & Automation Overview" (task rate/duration by name, queue depth) |
| What happened around a specific request? | Its `X-Request-Id` — grep backend logs, then the same ID appears as `request_id` in every worker log line for any job that request triggered (Phase 10 correlation-ID propagation, ADR-022) |
| Is a specific workflow/execution stuck? | `GET /v1/workflow-executions/{id}` or `/v1/execution-jobs/{id}` — both expose a full per-step timeline in the frontend's Execution/Workflow History views |
| Are alarms firing? | CloudWatch → the SNS topic's subscribed email (backend CPU, ALB 5xx rate, RDS storage/connections — `infrastructure/terraform/modules/monitoring`) |

## 3. Common incidents

### API returning 5xx
1. Check `/health/ready` — dependency issue (DB/Redis) vs. application bug.
2. Check the "Slowest routes" panel and recent deploys — a bad deploy usually shows as a step-change in the error-rate panel right after a deployment marker.
3. If it's a bad deploy: the `deploy` CI job's `deployment_circuit_breaker` should have already rolled back automatically; if not, dispatch the `rollback` job manually (Deployment Handbook §7).

### A scan/enrichment/embedding/recommendation job is stuck
1. Check its status via the relevant `GET` endpoint (`/v1/scans/{id}`, etc.) — `PENDING` for a long time means the worker isn't consuming; `RUNNING` for far longer than typical means it's actually stuck or crashed mid-task.
2. Check worker logs for that job's ID (correlation ID, §2 above) for an exception.
3. Scan/enrichment jobs retry automatically (job-level retry, 5x with backoff) — a job stuck in `RUNNING` past its `soft_time_limit` will be killed and, depending on the task, may need a manual re-trigger via its `POST .../cancel` then a fresh start.
4. Execution and workflow jobs do **not** auto-retry (a deliberate correctness choice, ADR-020/ADR-021 — a partially-applied mutation retried blind is a real risk) — a stuck one needs a human to inspect its step-level state before deciding to cancel, resume, or manually intervene in Drive.

### Scheduled workflow triggers aren't firing
1. Confirm exactly one Celery Beat process is running (`worker.scheduler.sweep` should appear in its logs every ~60s) — **never more than one**, or triggers double-fire (ADR-021).
2. Check `scheduler_jobs.next_run_at` for the trigger in question — if it's `NULL`, the trigger is disabled or its workflow isn't `ACTIVE`/published (the sweep intentionally leaves `next_run_at` unset in that case, meaning it never fires again until the trigger is re-enabled).

### Notifications aren't being delivered
- In-app notifications are real; check `GET /v1/notifications`.
- **Email is a stub by design this phase** (`NOTIFICATION_EMAIL_ENABLED` does not change this — see ADR-021) — nothing is broken if no email arrives, no real provider is configured yet.

### High memory/CPU on a worker
- Check the "Celery task duration" panel for which task type is running long — extraction (large PDFs) and embedding are the most memory-intensive stages.
- ECS Fargate tasks restart automatically on an OOM kill; if it's frequent for a specific task type, increase `worker_memory`/`worker_cpu` in the relevant `environments/*/main.tf` and redeploy.

## 4. Scaling

- **Backend/worker replica count:** `backend_desired_count`/`worker_desired_count` in `environments/*/main.tf` — redeploy after changing (no autoscaling policy is configured yet; see Known Issues in the [Release Readiness Report](phases/PHASE_10_COMPLETION_REPORT.md)).
- **Database:** vertical (`instance_class`) via Terraform; read replicas are not yet provisioned — a natural next step once read load actually justifies it.
- **Redis:** vertical (`node_type`); `multi_az = true` adds a replica with automatic failover, not additional read capacity.

## 5. Graceful shutdown behavior

- **Backend:** FastAPI's `lifespan` handler disposes the DB connection pool and closes the Redis client on `SIGTERM` before the process exits — an in-flight request completes normally; a new one isn't accepted once shutdown begins (standard ECS/uvicorn behavior).
- **Worker:** Celery's own "warm shutdown" on `SIGTERM` — stops accepting new tasks, lets in-flight ones finish (up to their time limit) before exiting. `task_acks_late=True` + `task_reject_on_worker_lost=True` mean a task killed mid-execution (hard `SIGKILL`, OOM) is redelivered to another worker, never silently dropped.

## 6. Log access

Structured JSON, one line per request/task (`vault_shared.logging.JSONFormatter`). Locally: `docker compose logs -f backend worker`. In AWS: CloudWatch Logs, one log group per service (`/ecs/<name-prefix>/{backend,worker,beat}`), retained per `log_retention_days` (default 30).

## 7. Runbook maintenance

Update this document whenever a new incident type is diagnosed for the first time in production — the goal is that the second occurrence of any given problem is a lookup, not a re-investigation.
