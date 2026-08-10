# infrastructure/docker

Container definitions for local development and deployment (Dockerfiles, compose files) for every service in `apps/*` plus supporting datastores.

- `backend.Dockerfile`, `worker.Dockerfile` — single-stage Python images. Both build with the **repo root** as context (not this directory) so they can `COPY packages/shared` alongside the app, preserving the relative path `apps/*/requirements.txt` uses to install it as an editable dependency (`-e ../../packages/shared`).
- `frontend.Dockerfile` — multi-stage: `development` (hot-reload dev server, used by compose), `build`, and `production` (static build served by nginx) — the last two aren't wired into compose yet; they're there for the Phase 8 release-hardening pass.
- `docker-compose.yml` — the full local stack: `postgres`, `redis`, `backend`, `worker`, `frontend`. Run from the **repo root**:

  ```bash
  cp .env.example .env
  docker compose -f infrastructure/docker/docker-compose.yml up
  ```

  Backend on `:8000`, frontend on `:5173`, Postgres on `:5432`, Redis on `:6379`.
