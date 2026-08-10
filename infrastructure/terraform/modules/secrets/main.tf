# AWS Secrets Manager (Phase 10, ADR-022's "secret management" deliverable).
# Every value the application currently reads from `.env` in local dev
# (see `.env.example`) gets its own secret here — ECS task definitions
# reference these by ARN (compute module's `secrets` block), which
# resolves them into the container's environment at start time. Nothing
# secret ever appears in a task definition, a Docker image, or Terraform
# state's plaintext (state itself should still be encrypted — see
# environments/production/backend.tf).

locals {
  secrets = {
    database_url             = var.database_url
    redis_url                = var.redis_url
    jwt_secret               = var.jwt_secret
    connector_encryption_key = var.connector_encryption_key
    google_client_secret     = var.google_client_secret
    sentry_dsn               = var.sentry_dsn
  }
}

resource "aws_secretsmanager_secret" "this" {
  for_each = local.secrets
  name     = "${var.name_prefix}/${each.key}"
  tags     = var.tags
}

resource "aws_secretsmanager_secret_version" "this" {
  for_each      = local.secrets
  secret_id     = aws_secretsmanager_secret.this[each.key].id
  secret_string = each.value
}
