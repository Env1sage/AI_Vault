# packages/types

Shared TypeScript type and interface definitions (API contracts, domain models, event payloads) consumed by `apps/frontend`. No runtime logic — types only.

Per ADR-012, `apps/backend` is Python (Pydantic), so these types are **not** shared zero-translation across the whole stack as ADR-002 originally envisioned — they're kept in sync by hand against the backend's OpenAPI schema for now. Generating this package from that schema (e.g. `openapi-typescript`) is flagged as future tooling work once the backend has a non-trivial API surface.
