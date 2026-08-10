variable "name_prefix" {
  type = string
}

variable "backup_retention_days" {
  description = "How long an object stays in the backups bucket before lifecycle-expiring — independent of, and normally longer than, infrastructure/scripts/backup.sh's local 14-file retention."
  type        = number
  default     = 90
}

variable "tags" {
  type    = map(string)
  default = {}
}
