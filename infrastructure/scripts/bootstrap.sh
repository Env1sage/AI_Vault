#!/usr/bin/env bash
# One-command local dev environment setup (Phase 1 Definition of Done:
# "local development is documented"). Idempotent — safe to re-run.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — review it before running docker compose up."
fi

if [ ! -f apps/frontend/.env ]; then
  cp apps/frontend/.env.example apps/frontend/.env
fi

echo "==> Installing JS workspace dependencies (pnpm)"
corepack enable
pnpm install

for app in backend worker; do
  echo "==> Setting up apps/$app Python virtualenv"
  python3 -m venv "apps/$app/.venv"
  (
    cd "apps/$app"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install --upgrade pip >/dev/null
    # requirements.txt's `-e ../../packages/shared` line is resolved by pip
    # relative to the current working directory, not the requirements file's
    # own location — this install must run with apps/$app as cwd.
    pip install -r requirements-dev.txt
  )
done

echo "==> Bootstrap complete."
echo "Next: docker compose -f infrastructure/docker/docker-compose.yml up"
