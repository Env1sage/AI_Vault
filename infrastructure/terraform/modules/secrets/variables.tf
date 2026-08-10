variable "name_prefix" {
  type = string
}

variable "database_url" {
  description = "Full DATABASE_URL, assembled by the environment root module from the database module's output + the master password variable."
  type        = string
  sensitive   = true
}

variable "redis_url" {
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

variable "google_client_secret" {
  type      = string
  sensitive = true
}

variable "sentry_dsn" {
  description = "Empty string leaves Sentry off (vault_shared/error_tracking.py's stub-until-configured behavior) — see ADR-021/ADR-022's stub pattern."
  type        = string
  sensitive   = true
  default     = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}
