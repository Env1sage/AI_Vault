# infrastructure/scripts

Operational scripts: environment bootstrap, migration runners, seed scripts, deployment helpers. Never contains business logic — orchestration only.

- `bootstrap.sh` — one-command local setup: copies `.env` files from their `.env.example`, installs the pnpm workspace, creates `apps/backend` and `apps/worker`'s Python virtualenvs. Idempotent.
- `migrate.sh` — runs `alembic upgrade head` against `apps/backend`'s `.venv`. For the dockerized stack, use `docker compose exec backend alembic upgrade head` instead.

No seed script yet — Phase 1 has no business tables to seed (Engineering Handbook §27's Definition of Done for this phase). Added once a phase introduces data worth seeding.
