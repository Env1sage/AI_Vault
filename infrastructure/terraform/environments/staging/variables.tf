variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "availability_zones" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"] # a target group/ALB still needs 2 AZs even in staging; single_nat_gateway=true below is the actual cost lever
}

variable "backend_image_tag" {
  type = string
}

variable "worker_image_tag" {
  type = string
}

variable "frontend_image_tag" {
  type = string
}

variable "container_registry" {
  type = string
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
