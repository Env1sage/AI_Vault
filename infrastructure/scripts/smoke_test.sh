#!/usr/bin/env bash
# Post-deploy smoke test (Phase 10, ADR-022). Hits the handful of endpoints
# that prove the deployed backend is actually serving traffic and can reach
# its own dependencies — not a full test suite, just the fast "did the
# deploy work at all" check CI runs immediately after `terraform apply`
# and a founder can run by hand after any deploy.
#
# Usage:
#   infrastructure/scripts/smoke_test.sh https://api.example.com
#   infrastructure/scripts/smoke_test.sh http://localhost:8000   # local dev
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <base-url>" >&2
  exit 1
fi

base_url="${1%/}"
failures=0

check() {
  local path="$1"
  local expected_status="$2"
  local url="${base_url}${path}"
  local status
  # curl itself prints "000" via -w on a connection failure/timeout — an
  # `|| echo "000"` fallback here would double up on top of that on some
  # curl versions/platforms, producing a nonsense "000000". `|| true`
  # only guards the non-zero exit status, never touches stdout.
  status="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" || true)"
  if [ "$status" = "$expected_status" ]; then
    echo "OK   $path -> $status"
  else
    echo "FAIL $path -> $status (expected $expected_status)"
    failures=$((failures + 1))
  fi
}

echo "==> Smoke testing $base_url"
check "/health/live" 200
check "/health/ready" 200
check "/v1/version" 200

if [ "$failures" -gt 0 ]; then
  echo "==> Smoke test FAILED ($failures check(s) failed)"
  exit 1
fi

echo "==> Smoke test passed"
