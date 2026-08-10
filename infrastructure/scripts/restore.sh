#!/usr/bin/env bash
# Database restore (Phase 10, ADR-022's Disaster Recovery deliverable) —
# the counterpart to backup.sh. Restores into whatever database
# `DATABASE_URL` points at; it does NOT create that database first, since
# "does the target already exist and is it the right one" is exactly the
# kind of question a script should never guess the answer to during an
# actual incident — see Docs/16_DISASTER_RECOVERY_GUIDE.md for the full
# drill procedure (create/recreate the target DB, then run this).
#
# Usage:
#   infrastructure/scripts/restore.sh infrastructure/backups/vault-20260804T060000Z.dump
#   DATABASE_URL=postgresql://... infrastructure/scripts/restore.sh <dump-file>
set -euo pipefail

DATABASE_URL="${DATABASE_URL:-postgresql://vault:vault@localhost:5432/vault}"

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <path-to-dump-file>" >&2
  exit 1
fi

dump_file="$1"
if [ ! -f "$dump_file" ]; then
  echo "No such backup file: $dump_file" >&2
  exit 1
fi

echo "==> Restoring $dump_file into $DATABASE_URL"
echo "==> This assumes the target database exists and is either empty or"
echo "    intended to be overwritten (--clean drops existing objects first)."
read -r -p "Continue? [y/N] " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
  echo "Aborted."
  exit 1
fi

pg_restore --clean --if-exists --no-owner --dbname="$DATABASE_URL" "$dump_file"

echo "==> Restore complete. Run 'alembic upgrade head' (infrastructure/scripts/migrate.sh)"
echo "    afterward if the backup predates the currently-deployed migrations."
