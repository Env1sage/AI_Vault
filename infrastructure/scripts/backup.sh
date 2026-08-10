#!/usr/bin/env bash
# Database backup (Phase 10, ADR-022's Disaster Recovery deliverable).
# Produces a timestamped, gzip-compressed `pg_dump -Fc` (custom format —
# required for `pg_restore`'s selective/parallel restore, unlike plain SQL)
# under `$BACKUP_DIR` (default: infrastructure/backups, gitignored).
#
# Usage:
#   infrastructure/scripts/backup.sh
#   BACKUP_DIR=/mnt/backups DATABASE_URL=postgresql://... infrastructure/scripts/backup.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/infrastructure/backups}"
DATABASE_URL="${DATABASE_URL:-postgresql://vault:vault@localhost:5432/vault}"

mkdir -p "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
out_file="$BACKUP_DIR/vault-${timestamp}.dump"

echo "==> Backing up $DATABASE_URL to $out_file"
pg_dump --format=custom --dbname="$DATABASE_URL" --file="$out_file"

size="$(du -h "$out_file" | cut -f1)"
echo "==> Backup complete: $out_file ($size)"

# Retention (Docs/16_DISASTER_RECOVERY_GUIDE.md's RPO section): keep the
# last 14 daily backups locally; anything older is assumed to already be
# in whatever off-host storage the production backup schedule uploads to
# (S3/GCS — see infrastructure/terraform/modules/storage), so pruning here
# never risks being the only copy. Written without `mapfile`/arrays —
# macOS still ships bash 3.2 (GPLv3 licensing), which has neither.
keep="${BACKUP_RETENTION_COUNT:-14}"
ls -1t "$BACKUP_DIR"/vault-*.dump 2>/dev/null | tail -n "+$((keep + 1))" | while IFS= read -r old; do
  echo "==> Pruning old backup: $old"
  rm -f "$old"
done
