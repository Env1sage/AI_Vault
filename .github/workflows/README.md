# .github/workflows

CI/CD pipeline definitions.

- `ci.yml` — **implemented in Phase 1.** Runs on every PR into `develop`/`main` and every push to `develop`: frontend (lint, typecheck, vitest, vite build), backend (ruff, mypy, alembic migration against a real Postgres service container, pytest unit+integration), worker (ruff, mypy, pytest unit), and a Docker image build validation job for all three Dockerfiles.

Still planned, not yet implemented (no phase has reached the milestone that needs them):

- `e2e.yml` — end-to-end suite on every PR into `main`. Deferred until a phase has a real critical-path flow (auth, scan → recommendation → execution) worth driving end-to-end; Phase 1's only e2e coverage is `tests/e2e/test_stack_boots.py`, run manually against `docker compose up`, not yet wired into CI.
- `deploy-staging.yml` — deploy `develop` to staging on merge.
- `deploy-production.yml` — deploy `main` to production on tagged release, gated on manual approval.

Both deploy workflows are blocked on ADR-009's open question — the actual deployment target (ECS, Kubernetes, a PaaS) — which is deliberately still undecided.
