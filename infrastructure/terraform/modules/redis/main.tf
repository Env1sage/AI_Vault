# ElastiCache Redis (Phase 10, ADR-022) — Celery's broker and result
# backend, and the backend's rate-limiter/cache store (`app/infrastructure/
# cache/redis_client.py`). A replication group (not a bare cache cluster)
# so production can turn on `automatic_failover_enabled` — losing Redis
# doesn't lose data (nothing here is durable state, see Docs/16_DISASTER_
# RECOVERY_GUIDE.md's "what's NOT backed up" section) but it does stall
# every queued job until it's back, so failover matters for availability
# even though it doesn't matter for durability.

resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.name_prefix}-redis"
  subnet_ids = var.private_subnet_ids
  tags       = var.tags
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.name_prefix}-redis-"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from the application's ECS tasks only"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.allowed_security_group_ids
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-redis-sg" })
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "${var.name_prefix}-redis"
  description          = "AI Project Vault — Celery broker/result backend + rate-limit store"

  engine         = "redis"
  engine_version = "7.1"
  node_type      = var.node_type
  port           = 6379

  num_cache_clusters         = var.multi_az ? 2 : 1
  automatic_failover_enabled = var.multi_az
  multi_az_enabled           = var.multi_az

  subnet_group_name  = aws_elasticache_subnet_group.this.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  tags = var.tags
}
