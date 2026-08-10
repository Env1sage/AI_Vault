variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "availability_zones" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

variable "backend_image_tag" {
  description = "Set via TF_VAR_backend_image_tag by the CI deploy job (.github/workflows/ci.yml) — the git SHA of the image just built."
  type        = string
}

variable "worker_image_tag" {
  type = string
}

variable "frontend_image_tag" {
  # Accepted (CI's deploy job always sets it) but not yet wired to a real
  # resource here — the frontend's production deployment target
  # (CloudFront+S3 vs. the frontend Docker image behind its own ALB
  # listener) is an org-specific choice the Deployment Handbook flags as
  # a follow-up rather than assumed. See Docs/04_DEPLOYMENT_HANDBOOK.md.
  type = string
}

variable "container_registry" {
  description = "e.g. 123456789012.dkr.ecr.us-east-1.amazonaws.com"
  type        = string
}

variable "database_master_password" {
  type      = string
  sensitive = true
}

variable "jwt_secret" {
  type      = string
  sensitive = true
}

variable "connector_encryption_key" {
  type      = string
  sensitive = true
}

variable "google_client_id" {
  type = string
}

variable "google_client_secret" {
  type      = string
  sensitive = true
}

variable "sentry_dsn" {
  type      = string
  sensitive = true
  default   = ""
}

variable "acm_certificate_arn" {
  type = string
}

variable "pager_email" {
  type = string
}
