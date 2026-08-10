# Phase 05 — AI Intelligence

**Status:** ⬜ Not started — placeholder. To be expanded into a full spec by the CTO role before implementation begins, per [Engineering Handbook §27](../00_ENGINEERING_HANDBOOK.md#27-documentation-standards). Depends on Phase 4.

## Objective

Implement the AI Gateway (ADR-007) in `packages/shared` with at least two provider adapters wired from the start, and build the recommendation engine on top of it, combining Phase 4's signals with AI Gateway output into rationale-and-confidence-scored proposed actions.

## Architecture

TBD when scoped. Must conform to [Engineering Handbook §12](../00_ENGINEERING_HANDBOOK.md#12-ai-philosophy) — only `packages/shared` imports provider SDKs; callers use capability-based methods only. Recommendation engine per §8.6 never executes, only proposes.

## API changes

TBD when scoped.

## Database changes

TBD when scoped. Expected: recommendations table (proposed action, rationale, confidence, status).

## Folder changes

TBD when scoped. Populates `packages/shared`'s AI Gateway module and its per-provider adapters.

## Backend changes

TBD when scoped.

## Frontend changes

TBD when scoped. Expected: none — recommendation UI arrives Phase 6.

## Security

TBD when scoped. Provider API keys are secrets per [Handbook §13](../00_ENGINEERING_HANDBOOK.md#13-security-philosophy); confirm no prompt/response content containing PII is logged.

## Tests

TBD when scoped. Expected: Gateway interface tested against every wired provider adapter with the same test suite (proves provider-swap parity, per ADR-007's guarantee).

## Manual checklist

- [ ] TBD when scoped.

## Definition of Done

- [ ] TBD when scoped.
