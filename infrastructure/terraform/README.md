# infrastructure/terraform

Infrastructure-as-Code for AI Project Vault (Phase 10, ADR-022). A reference
implementation targeting AWS — the resource *shapes* (compute, managed
Postgres, managed Redis, load balancer, object storage, secret management,
networking, logging, monitoring) are the cloud-provider-agnostic part the
Phase 10 spec asked for; the actual resources below are AWS-specific
because *some* provider has to be picked to write runnable code, not
because the architecture assumes AWS. Porting to another provider means
rewriting the modules under `modules/`, not the applications themselves —
`apps/backend`, `apps/worker`, and `apps/frontend` know nothing about
Terraform or AWS.

**Not applied against a real AWS account as part of this phase** — there is
no cloud account available in this environment. Every module is
syntactically reviewed and internally consistent (variable references,
module wiring), but `terraform validate`/`plan`/`apply` have not been run
against real AWS credentials. Review with a real AWS account and adjust
sizing/naming/tagging to your org's conventions before the first real
`apply`. See `Docs/04_DEPLOYMENT_HANDBOOK.md` for the full deployment
procedure this fits into.

## Layout

```text
modules/
  network/         VPC, public/private subnets, NAT, security groups
  database/        RDS PostgreSQL (Multi-AZ in production)
  redis/            ElastiCache Redis (Celery broker/result backend)
  storage/          S3 buckets — backups (infrastructure/scripts/backup.sh
                    uploads here) and, later, any object storage the
                    connector platform itself might need
  secrets/          AWS Secrets Manager — DB credentials, JWT secret,
                    CONNECTOR_ENCRYPTION_KEY, SENTRY_DSN, etc.
  compute/          ECS Fargate cluster + task definitions/services for
                    backend, worker, and a separate Celery Beat service
                    (Phase 9's scheduler needs exactly one Beat process
                    running, never more — see ADR-021)
  load_balancer/    ALB in front of the backend service + frontend's
                    static assets (served from S3+CloudFront or the
                    frontend Docker image — see environments/*/main.tf)
  monitoring/       CloudWatch log groups, alarms, SNS topic for paging

environments/
  staging/          Smaller instance sizes, single-AZ, shorter backup
                     retention — cheap to run, not meant to survive an AZ
                     failure.
  production/        Multi-AZ RDS, autoscaled ECS services, longer backup
                     retention, alarms wired to a real paging destination.
```

## Remote state

Each environment's `backend.tf` expects an S3 bucket + DynamoDB lock table
for remote state — created once, by hand, before the first `terraform
init` (a chicken-and-egg problem Terraform can't solve for its own state
storage). See the comment at the top of `environments/production/backend.tf`.

## Usage

```bash
cd infrastructure/terraform/environments/staging
terraform init
terraform plan   -var-file=terraform.tfvars
terraform apply  -var-file=terraform.tfvars
```

The `deploy` job in `.github/workflows/ci.yml` runs the equivalent
non-interactively (`terraform apply -auto-approve`), gated behind a manual
`workflow_dispatch` and a GitHub Environment approval — see that
workflow's comments.
