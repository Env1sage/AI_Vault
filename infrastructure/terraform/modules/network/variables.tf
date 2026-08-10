variable "name_prefix" {
  description = "Prefix applied to every resource name/tag (e.g. \"vault-staging\")."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "AZs to spread public/private subnets across. Two is the minimum for an RDS Multi-AZ deployment and an ALB."
  type        = list(string)
}

variable "single_nat_gateway" {
  description = "true for staging (one NAT, cheaper, single point of failure); false for production (one NAT per AZ)."
  type        = bool
  default     = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
