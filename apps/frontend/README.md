# apps/frontend

Web client for AI Project Vault. Owns presentation-layer code only — no domain logic, no direct data-store access, no direct AI provider calls.

Talks to `apps/backend` over the documented API surface (`src/lib/api-client.ts`), and to no other service directly.

Vite + React 19 + TypeScript SPA (ADR-012 — not Next.js), Tailwind CSS v4, TanStack Router (file-based, `src/routes/`) + TanStack Query, Zustand, React Hook Form + Zod, shadcn/ui conventions (`components.json`, `src/components/ui/`).

Phase 1 shipped the application shell only (error boundary, loading screen, a health/version widget). 

## Local development

```bash
pnpm install
cp .env.example .env   # set VITE_GOOGLE_CLIENT_ID to test Google sign-in
pnpm dev
```

## Scripts

`pnpm dev` · `pnpm build` · `pnpm lint` · `pnpm typecheck` · `pnpm test`

