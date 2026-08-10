#!/usr/bin/env bash
# Runs Alembic migrations against DATABASE_URL (from apps/backend's .venv or
# repo-root .env). When the stack is running under docker compose instead,
# use `docker compose -f infrastructure/docker/docker-compose.yml exec backend alembic upgrade head`.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/apps/backend"

if [ ! -d .venv ]; then
  echo "apps/backend/.venv not found — run infrastructure/scripts/bootstrap.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate
alembic upgrade head
