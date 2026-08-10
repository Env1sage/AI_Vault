output "dns_name" {
  value = aws_lb.this.dns_name
}

output "backend_target_group_arn" {
  value = aws_lb_target_group.backend.arn
}

# CloudWatch's ALB/target-group metrics are dimensioned by "arn_suffix"
# (e.g. "app/vault-production-alb/50dc6c495c0c9188"), not the full ARN or
# the DNS name — the monitoring module needs these two, specifically.
output "arn_suffix" {
  value = aws_lb.this.arn_suffix
}

output "backend_target_group_arn_suffix" {
  value = aws_lb_target_group.backend.arn_suffix
}
