# 04 — Deployment & Operations Handbook

Status: **Living document**, introduced in Phase 10 (ADR-022). Covers cloud deployment, environment promotion, and the CI/CD pipeline that automates both. For local development, see the root [`README.md`](../README.md) and each app's own README. For what to do when something breaks in production, see the [Operations Runbook](09_OPERATIONS_RUNBOOK.md) and [Disaster Recovery Guide](10_DISASTER_RECOVERY_GUIDE.md).

---

## 1. Environments

| Environment | Purpose | Sizing | HA | Backup retention |
|---|---|---|---|---|
| **Development** | Local machine, `docker compose up` | N/A | N/A | N/A (local Postgres only) |
| **Staging** | Pre-production validation, single-AZ, cheap to run | `db.t4g.micro` / `cache.t4g.micro` / 1 backend+worker task each | No | 7 days (RDS), 30 days (S3) |
| **Production** | Real customer traffic | `db.r6g.large` / `cache.r6g.large` / 2+ backend+worker tasks | Multi-AZ RDS + Redis, 2+ ECS tasks per service | 30 days (RDS), 365 days (S3) |

Staging and production are defined in `infrastructure/terraform/environments/{staging,production}/` — structurally identical module graphs (same modules, same wiring), differing only in sizing/HA variables. See `infrastructure/terraform/README.md` for the full module layout.

## 2. Infrastructure as Code

All cloud infrastructure is Terraform, targeting AWS as the reference implementation (ADR-022 — the module boundaries, not AWS itself, are the "provider-agnostic" part). See `infrastructure/terraform/README.md`.

**Status:** every module and both environments pass `terraform fmt -check` and `terraform validate` with zero errors/warnings. **Not applied against a real AWS account** — no cloud account exists in this project's development environment. Review sizing, naming, and tagging conventions against your org's standards before the first real `apply`.

### One-time setup (per environment, before the first `terraform init`)

1. Create the remote-state bucket and lock table (see the comment atop `environments/<env>/backend.tf` for the exact AWS CLI commands).
2. Create an ACM certificate for your domain (DNS-validated, outside Terraform — validation needs your real DNS zone).
3. Populate `terraform.tfvars` from `terraform.tfvars.example` (never commit the real file).
4. `terraform init && terraform plan -var-file=terraform.tfvars` — review before ever running `apply`.

### What's provisioned

Network (VPC, public/private subnets, NAT) → Database (RDS PostgreSQL, encrypted, Multi-AZ in production) → Redis (ElastiCache, encrypted, automatic failover in production) → Storage (S3 for backups) → Secrets (Secrets Manager — every value in `.env.example` gets its own secret, read into ECS tasks at start time, never baked into an image) → Load Balancer (ALB, HTTPS-only with an HTTP→HTTPS redirect) → Compute (ECS Fargate — three services: `backend`, `worker`, and `beat`, the last hardcoded to `desired_count = 1` always, since two Celery Beat processes would double-fire every scheduled workflow trigger — see ADR-021) → Monitoring (CloudWatch alarms — CPU, ALB 5xx rate, RDS storage/connections — wired to an SNS topic with an email subscription).

The frontend's own production deployment target (CloudFront+S3 vs. its own Docker image behind a second ALB listener) is intentionally not decided here — an org-specific choice, not something the reference architecture should assume. `frontend_image_tag` is accepted as a Terraform variable (CI already builds and can push the image) but not yet wired to a real resource.

## 3. Containerization

Three images, each with a `HEALTHCHECK`: `infrastructure/docker/backend.Dockerfile`, `worker.Dockerfile` (single-stage, `python:3.13-slim`, non-root `vault_app` user as of Phase 10), `frontend.Dockerfile` (multi-stage: `development` target for local hot-reload, `production` target — static build served by `nginx:1.27-alpine`).

Image vulnerability scanning: CI's `docker-build` job builds all three and runs `aquasecurity/trivy-action` against each, failing on any CRITICAL/HIGH finding with an available fix (`ignore-unfixed: true` — an unfixable CVE failing every build is noise, not safety).

## 4. Environment variables and secrets

Every variable is documented in the repo-root `.env.example`, organized by the phase that introduced it. In AWS, each becomes a Secrets Manager entry (`infrastructure/terraform/modules/secrets/`) except `GOOGLE_CLIENT_ID` (not secret — sent to the browser as-is for Google Identity Services) and `ENVIRONMENT` (a plain, non-secret config value).

Two variables are intentionally stub-until-configured, per ADR-018/ADR-021/ADR-022's consistent pattern — leaving them unset does not break anything, it just leaves that integration off:

- `SENTRY_DSN` — empty means no error tracking is sent anywhere (`vault_shared/error_tracking.py`).
- `OTEL_EXPORTER_OTLP_ENDPOINT` — empty means distributed tracing spans are created and immediately discarded (OpenTelemetry's own no-op default provider).

## 5. CI/CD pipeline (`.github/workflows/ci.yml`)

| Job | Trigger | What it does |
|---|---|---|
| `frontend` | every PR/push | lint, typecheck, test, build |
| `backend` | every PR/push | lint, typecheck (app + `packages/shared` directly — see ADR-021/ADR-022's "check shared code from its own location" lesson), migrate against real Postgres, unit+integration tests |
| `worker` | every PR/push | same shape as `backend` |
| `security` | every PR/push | `pip-audit` (backend + worker), `pnpm audit`, `gitleaks` secret scan |
| `docker-build` | every PR/push | builds all three images, Trivy-scans each |
| `deploy` | **manual `workflow_dispatch` only** | builds+pushes images, `terraform apply`, post-deploy smoke test — gated behind a GitHub Environment approval (configure required reviewers on `staging`/`production` in repo Settings) |
| `rollback` | automatic, only if `deploy` fails | re-applies the last known-good image tag, same environment gate as `deploy` |

**Deployment is never automatic on push to any branch.** Triggering a real deploy requires: (1) dispatching the workflow with a target environment, (2) that environment's approval gate being satisfied, (3) the relevant secrets (`CONTAINER_REGISTRY`, cloud credentials, `LAST_KNOWN_GOOD_IMAGE_TAG` for rollback) actually being configured. None of the three exist yet in this repository — dispatching today fails fast and safely at the first missing secret.

## 6. Deployment procedure (once secrets are configured)

1. Merge to `main` (or whatever branch your release process uses) — CI's non-deploy jobs run and must be green.
2. From the Actions tab, manually dispatch the `CI` workflow with `target_environment: staging`.
3. Approve the `staging` Environment gate when prompted.
4. Watch `deploy` — image build/push, `terraform apply`, smoke test. ECS's `deployment_circuit_breaker` (`rollback = true`) automatically reverts if the new tasks never pass the ALB health check.
5. Run through the [Manual QA Checklist](phases/PHASE_10_COMPLETION_REPORT.md) against staging.
6. Repeat with `target_environment: production`.
7. Post-deploy: run `infrastructure/scripts/smoke_test.sh <production-url>` by hand as a second confirmation, and watch the Grafana dashboards (see [Monitoring Guide](11_MONITORING_GUIDE.md)) for the first 15-30 minutes.

## 7. Rollback

Automatic on a failed `deploy` (see table above). To roll back manually (e.g., a deploy succeeded but a bug surfaced afterward): dispatch the workflow again with the previous known-good `backend_image_tag`/`worker_image_tag`/`frontend_image_tag` values, or set `LAST_KNOWN_GOOD_IMAGE_TAG` and run the `rollback` job's `terraform apply` step by hand. Database migrations are additive-only by Alembic convention across every phase so far (no destructive schema change has ever shipped) — a code rollback does not require a corresponding down-migration in the common case; verify this holds before rolling back across a release that did change the schema destructively.

## 8. Database migrations

`alembic upgrade head`, run automatically by CI against a fresh Postgres container on every PR (proves migrations apply cleanly from empty). In production, run migrations as a one-off task before the new ECS task definition's containers start serving traffic — `infrastructure/scripts/migrate.sh` is the same script used locally, parameterized by `DATABASE_URL`.
