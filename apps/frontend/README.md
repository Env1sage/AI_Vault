# apps/frontend

Web client for AI Project Vault. Owns presentation-layer code only — no domain logic, no direct data-store access, no direct AI provider calls.

Talks to `apps/backend` over the documented API surface (`src/lib/api-client.ts`), and to no other service directly.

Vite + React 19 + TypeScript SPA (ADR-012 — not Next.js), Tailwind CSS v4, TanStack Router (file-based, `src/routes/`) + TanStack Query, Zustand, React Hook Form + Zod, shadcn/ui conventions (`components.json`, `src/components/ui/`).

Phase 1 shipped the application shell only (error boundary, loading screen, a health/version widget). Phase 2 added the Identity & Organization Platform: `/login` (Google Identity Services button), a protected `/dashboard`/`/profile`/`/organization` shell with RBAC-aware route guards, `/unauthorized`, a Zustand auth store (`src/stores/auth-store.ts`) with silent session recovery and automatic 401-refresh-retry (`src/lib/session.ts`, `src/lib/api-client.ts`) — see [ADR-013](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-013-phase-2-session-strategy--client-side-google-identity-services-short-lived-jwt--rotating-httponly-refresh-cookie). Phase 3 adds `/storage-connections` (list/connect/verify/disconnect Google Workspace) and `/connectors/google/callback` (completes the server-side OAuth exchange after Google's redirect) — see [ADR-014](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-014-phase-3-google-workspace-connector--server-side-authorization-code-flow-with-a-frontend-hosted-callback-encrypted-token-storage). Phase 4 adds `/scans` (current-scan progress polling, start/cancel actions, scan history, last-successful-scan) — see [`Docs/phases/PHASE_04_STORAGE_INTELLIGENCE.md`](../../Docs/phases/PHASE_04_STORAGE_INTELLIGENCE.md). Phase 5 adds `/files` (file browser) and `/files/$fileId` (metadata panel, classification, extraction status, knowledge attributes, related-files list), plus an "Enrichment" status/progress section on `/scans` — see [ADR-017](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-017-knowledge-engine-phase-5--deterministic-first-pipeline-content-extraction-and-scanenrichment-chaining). Phase 6 adds `/search` (query box, ranked results with a retrieval-method badge and score, linking into `/files/$fileId`) and `/chat` + `/chat/$conversationId` (conversation list, message thread, a per-message citation panel linking to file detail), plus an "Embedding" status/progress section on `/scans` mirroring Enrichment's — see [ADR-018](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-018-ai-intelligence-engine-phase-6--ai-gateway-abstraction-local-first-embeddings-mean-centered-similarity-and-a-stubbed-completion-provider). 

## Local development

```bash
pnpm install
cp .env.example .env   # set VITE_GOOGLE_CLIENT_ID to test Google sign-in
pnpm dev
```

## Scripts

`pnpm dev` · `pnpm build` · `pnpm lint` · `pnpm typecheck` · `pnpm test`

