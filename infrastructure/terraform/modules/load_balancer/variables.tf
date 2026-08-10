variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "alb_security_group_id" {
  type = string
}

variable "acm_certificate_arn" {
  description = "ACM certificate for the HTTPS listener — issued/validated outside Terraform (DNS validation needs the domain's real zone, which varies per org)."
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
