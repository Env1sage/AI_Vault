# ECS Fargate (Phase 10, ADR-022) — three long-running services sharing
# one cluster: backend (behind the ALB), worker (Celery worker processes,
# horizontally scaled), and beat (Celery Beat — the scheduler that fires
# `worker.scheduler.sweep` every 60s per ADR-021; `desired_count` is
# hardcoded to 1 below and must never be raised, since two Beat processes
# would double-fire every scheduled workflow trigger).

resource "aws_ecs_cluster" "this" {
  name = "${var.name_prefix}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = var.tags
}

# The ECS tasks' security group is owned by the network module, not here —
# see that module's comment for why (breaking a circular module
# dependency: database/redis need to reference this SG's ID too, and this
# module needs database/redis's connection info via the secrets module).

resource "aws_iam_role" "execution" {
  name = "${var.name_prefix}-ecs-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Least-privilege beyond the managed policy above (Handbook §13) — the
# execution role additionally needs to read exactly the secrets this app
# uses, not every secret in the account.
resource "aws_iam_role_policy" "execution_secrets" {
  name = "${var.name_prefix}-read-app-secrets"
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = values(var.secret_arns)
    }]
  })
}

resource "aws_iam_role" "task" {
  name = "${var.name_prefix}-ecs-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.name_prefix}/backend"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.name_prefix}/worker"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "beat" {
  name              = "/ecs/${var.name_prefix}/beat"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

locals {
  # Every task (backend/worker/beat) reads the identical set of secrets —
  # they all read the same DATABASE_URL/REDIS_URL/etc. via vault_shared's
  # Settings, same as local dev's shared .env.
  app_secrets = [for name, arn in var.secret_arns : {
    name      = upper(name)
    valueFrom = arn
  }]
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.name_prefix}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name         = "backend"
    image        = var.backend_image
    essential    = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "GOOGLE_CLIENT_ID", value = var.google_client_id },
      { name = "ENVIRONMENT", value = "production" },
    ]
    secrets = local.app_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.backend.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "backend"
      }
    }
    healthCheck = {
      command  = ["CMD-SHELL", "curl -f http://localhost:8000/health/live || exit 1"]
      interval = 30
      timeout  = 5
      retries  = 3
    }
  }])

  tags = var.tags
}

resource "aws_ecs_service" "backend" {
  name            = "${var.name_prefix}-backend"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.ecs_tasks_security_group_id]
  }

  load_balancer {
    target_group_arn = var.backend_target_group_arn
    container_name   = "backend"
    container_port   = 8000
  }

  # Zero-downtime deploys (Phase 10's Deployment deliverable) — ECS starts
  # the new task set and waits for it to pass the ALB health check before
  # draining the old one; deployment_circuit_breaker rolls back
  # automatically if the new tasks never become healthy, rather than
  # leaving the service stuck mid-rollout.
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = var.tags
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.name_prefix}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "worker"
    image     = var.worker_image
    essential = true
    command   = ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
    environment = [
      { name = "ENVIRONMENT", value = "production" },
    ]
    secrets = local.app_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.worker.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])

  tags = var.tags
}

resource "aws_ecs_service" "worker" {
  name            = "${var.name_prefix}-worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.ecs_tasks_security_group_id]
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  tags = var.tags
}

resource "aws_ecs_task_definition" "beat" {
  family                   = "${var.name_prefix}-beat"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "beat"
    image     = var.worker_image
    essential = true
    command   = ["celery", "-A", "worker.celery_app", "beat", "--loglevel=info"]
    environment = [
      { name = "ENVIRONMENT", value = "production" },
    ]
    secrets = local.app_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.beat.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "beat"
      }
    }
  }])

  tags = var.tags
}

resource "aws_ecs_service" "beat" {
  name            = "${var.name_prefix}-beat"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.beat.arn
  # Exactly one, always — see this file's top comment.
  desired_count = 1
  launch_type   = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.ecs_tasks_security_group_id]
  }

  tags = var.tags
}

# `.name` (not `.region`) deliberately — `.region` only exists on the AWS
# provider v6 line; environments/*/providers.tf pins `~> 5.0`, where `.name`
# is the only attribute that exists (soft-deprecated there, but present).
# Revisit both together if the environments ever move to v6.
data "aws_region" "current" {}
