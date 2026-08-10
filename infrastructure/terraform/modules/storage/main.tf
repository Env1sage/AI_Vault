# S3 — backup storage (Phase 10, ADR-022's Disaster Recovery deliverable).
# infrastructure/scripts/backup.sh writes locally; production wraps it (or
# a `sync` step) to push each dump here so a single-host disk failure
# can't also take the backups with it. Versioned + encrypted + no public
# access, ever.

resource "aws_s3_bucket" "backups" {
  bucket = "${var.name_prefix}-backups"
  tags   = var.tags
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    id     = "expire-old-backups"
    status = "Enabled"
    # Applies to every object in the bucket — this bucket holds nothing
    # but backups, so an empty filter (not a prefix restriction) is
    # correct, not just the minimal one that satisfies the provider.
    filter {}
    expiration {
      days = var.backup_retention_days
    }
    noncurrent_version_expiration {
      noncurrent_days = var.backup_retention_days
    }
  }
}
