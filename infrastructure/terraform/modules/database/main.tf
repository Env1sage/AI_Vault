# RDS PostgreSQL (Phase 10, ADR-022). Encrypted at rest (`storage_encrypted`)
# and in transit (the application's DATABASE_URL uses `sslmode=require`,
# see environments/*/main.tf) — the same "encryption at rest/in transit"
# requirement the phase spec names, at the infrastructure layer this time,
# not just for connector OAuth tokens (that's Fernet, in `packages/shared`).

resource "aws_db_subnet_group" "this" {
  name       = "${var.name_prefix}-db"
  subnet_ids = var.private_subnet_ids
  tags       = var.tags
}

resource "aws_security_group" "db" {
  name_prefix = "${var.name_prefix}-db-"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Postgres from the application's ECS tasks only"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_group_ids
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-db-sg" })
}

resource "aws_db_instance" "this" {
  identifier     = "${var.name_prefix}-postgres"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage_gb
  max_allocated_storage = var.allocated_storage_gb * 5 # storage autoscaling ceiling
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.database_name
  username = var.master_username
  password = var.master_password

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  multi_az                  = var.multi_az
  backup_retention_period   = var.backup_retention_days
  backup_window             = "03:00-04:00" # low-traffic UTC window; adjust per org
  maintenance_window        = "sun:04:30-sun:05:30"
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.name_prefix}-postgres-final"

  performance_insights_enabled = true

  tags = var.tags
}
