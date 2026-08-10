output "cluster_id" {
  value = aws_ecs_cluster.this.id
}

# CloudWatch's AWS/ECS metrics are dimensioned by the cluster's plain
# name, not its ARN (`cluster_id` above is the ARN in provider v5+) —
# the monitoring module needs this one specifically.
output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "backend_service_name" {
  value = aws_ecs_service.backend.name
}
