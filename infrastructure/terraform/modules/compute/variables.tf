variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "ecs_tasks_security_group_id" {
  description = "From the network module — owned there to avoid a circular module dependency, see that module's comment."
  type        = string
}

variable "backend_image" {
  description = "Full image URI, e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/vault-backend:sha-abc123"
  type        = string
}

variable "worker_image" {
  type = string
}

variable "backend_target_group_arn" {
  description = "From the load_balancer module — the ALB target group the backend service registers with."
  type        = string
}

variable "secret_arns" {
  description = "From the secrets module — {database_url, redis_url, jwt_secret, connector_encryption_key, google_client_secret, sentry_dsn} => ARN."
  type        = map(string)
}

variable "google_client_id" {
  description = "Not secret (it's sent to the browser as-is for Google Identity Services) — a plain env var, not a Secrets Manager entry."
  type        = string
}

variable "backend_cpu" {
  type    = number
  default = 512
}

variable "backend_memory" {
  type    = number
  default = 1024
}

variable "backend_desired_count" {
  type    = number
  default = 2
}

variable "worker_cpu" {
  type    = number
  default = 1024
}

variable "worker_memory" {
  type    = number
  default = 2048
}

variable "worker_desired_count" {
  type    = number
  default = 2
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "tags" {
  type    = map(string)
  default = {}
}
