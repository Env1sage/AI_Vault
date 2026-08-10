locals {
  name_prefix = "vault-production"
  tags = {
    Project     = "ai-project-vault"
    Environment = "production"
  }
}

module "network" {
  source             = "../../modules/network"
  name_prefix        = local.name_prefix
  availability_zones = var.availability_zones
  single_nat_gateway = false # one NAT per AZ — a single NAT is a single point of failure Multi-AZ RDS shouldn't sit behind
  tags               = local.tags
}

module "database" {
  source                     = "../../modules/database"
  name_prefix                = local.name_prefix
  vpc_id                     = module.network.vpc_id
  private_subnet_ids         = module.network.private_subnet_ids
  allowed_security_group_ids = [module.network.ecs_tasks_security_group_id]
  instance_class             = "db.r6g.large"
  allocated_storage_gb       = 100
  multi_az                   = true
  backup_retention_days      = 30
  master_password            = var.database_master_password
  tags                       = local.tags
}

module "redis" {
  source                     = "../../modules/redis"
  name_prefix                = local.name_prefix
  vpc_id                     = module.network.vpc_id
  private_subnet_ids         = module.network.private_subnet_ids
  allowed_security_group_ids = [module.network.ecs_tasks_security_group_id]
  node_type                  = "cache.r6g.large"
  multi_az                   = true
  tags                       = local.tags
}

module "storage" {
  source                = "../../modules/storage"
  name_prefix           = local.name_prefix
  backup_retention_days = 365 # production keeps a year of off-host backups; local retention (backup.sh) is still just 14
  tags                  = local.tags
}

module "secrets" {
  source                   = "../../modules/secrets"
  name_prefix              = local.name_prefix
  database_url             = "postgresql+psycopg://${module.database.database_name}:${var.database_master_password}@${module.database.endpoint}/${module.database.database_name}?sslmode=require"
  redis_url                = "redis://${module.redis.primary_endpoint}:6379/0"
  jwt_secret               = var.jwt_secret
  connector_encryption_key = var.connector_encryption_key
  google_client_secret     = var.google_client_secret
  sentry_dsn               = var.sentry_dsn
  tags                     = local.tags
}

module "load_balancer" {
  source                = "../../modules/load_balancer"
  name_prefix           = local.name_prefix
  vpc_id                = module.network.vpc_id
  public_subnet_ids     = module.network.public_subnet_ids
  alb_security_group_id = module.network.alb_security_group_id
  acm_certificate_arn   = var.acm_certificate_arn
  tags                  = local.tags
}

module "compute" {
  source                      = "../../modules/compute"
  name_prefix                 = local.name_prefix
  vpc_id                      = module.network.vpc_id
  private_subnet_ids          = module.network.private_subnet_ids
  ecs_tasks_security_group_id = module.network.ecs_tasks_security_group_id
  backend_image               = "${var.container_registry}/vault-backend:${var.backend_image_tag}"
  worker_image                = "${var.container_registry}/vault-worker:${var.worker_image_tag}"
  backend_target_group_arn    = module.load_balancer.backend_target_group_arn
  secret_arns                 = module.secrets.secret_arns
  google_client_id            = var.google_client_id
  backend_desired_count       = 2
  worker_desired_count        = 2
  tags                        = local.tags
}

module "monitoring" {
  source                          = "../../modules/monitoring"
  name_prefix                     = local.name_prefix
  ecs_cluster_name                = module.compute.cluster_name
  backend_service_name            = module.compute.backend_service_name
  alb_arn_suffix                  = module.load_balancer.arn_suffix
  backend_target_group_arn_suffix = module.load_balancer.backend_target_group_arn_suffix
  rds_instance_id                 = module.database.instance_id
  pager_email                     = var.pager_email
  tags                            = local.tags
}
