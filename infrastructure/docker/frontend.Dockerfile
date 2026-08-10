# Build context is the repo root — the frontend depends on workspace
# packages (@vault/types, @vault/config) that live outside apps/frontend.
FROM node:22-slim AS base

WORKDIR /workspace

RUN corepack enable

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml turbo.json ./
COPY packages/config ./packages/config
COPY packages/types ./packages/types
COPY packages/ui ./packages/ui
COPY apps/frontend ./apps/frontend

RUN pnpm install --frozen-lockfile

# ---- development (used by docker-compose.yml for local dev / hot reload) ----
FROM base AS development

WORKDIR /workspace/apps/frontend

EXPOSE 5173

CMD ["pnpm", "dev", "--", "--host", "0.0.0.0"]

# ---- production build ----
FROM base AS build

RUN pnpm --filter @vault/frontend build

# ---- production (static file server) ----
FROM nginx:1.27-alpine AS production

COPY --from=build /workspace/apps/frontend/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD wget -qO- http://localhost:80 || exit 1
