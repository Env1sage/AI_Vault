output "secret_arns" {
  description = "Map of secret name -> ARN, for the compute module's ECS task definitions to reference."
  value       = { for k, s in aws_secretsmanager_secret.this : k => s.arn }
}
