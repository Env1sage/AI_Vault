variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security groups allowed to reach Postgres on 5432 — the compute module's ECS task security groups."
  type        = list(string)
}

variable "instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "allocated_storage_gb" {
  type    = number
  default = 20
}

variable "multi_az" {
  description = "Phase 10's RTO/RPO targets (Docs/16_DISASTER_RECOVERY_GUIDE.md) require this true in production."
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  type    = number
  default = 7
}

variable "database_name" {
  type    = string
  default = "vault"
}

variable "master_username" {
  type    = string
  default = "vault"
}

variable "master_password" {
  description = "Set via TF_VAR_database_master_password in CI, never committed — see secrets module for how the running application reads this instead of it being baked into a task definition."
  type        = string
  sensitive   = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
