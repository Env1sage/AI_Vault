output "alb_dns_name" {
  value = module.load_balancer.dns_name
}

output "database_endpoint" {
  value     = module.database.endpoint
  sensitive = true
}

output "backups_bucket_name" {
  value = module.storage.backups_bucket_name
}

output "ecs_cluster_name" {
  value = module.compute.cluster_name
}
