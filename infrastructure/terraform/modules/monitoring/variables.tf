variable "name_prefix" {
  type = string
}

variable "ecs_cluster_name" {
  type = string
}

variable "backend_service_name" {
  type = string
}

variable "alb_arn_suffix" {
  description = "The ALB's arn_suffix (not full ARN) — CloudWatch's ALB metrics dimension format."
  type        = string
}

variable "backend_target_group_arn_suffix" {
  type = string
}

variable "rds_instance_id" {
  type = string
}

variable "pager_email" {
  description = "Where alarm notifications go. A real pager/Slack/PagerDuty integration is a follow-up (subscribe an SNS-compatible endpoint to this topic) — email is the zero-setup default so alarms are never silently unwired."
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
