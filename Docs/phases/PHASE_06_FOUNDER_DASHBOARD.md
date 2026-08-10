# Phase 06 — Founder Dashboard

**Status:** ⬜ Not started — placeholder. To be expanded into a full spec by the CTO role before implementation begins, per [Engineering Handbook §27](../00_ENGINEERING_HANDBOOK.md#27-documentation-standards). Depends on Phase 5 (and Phase 2 for auth).

## Objective

Build `apps/frontend`: inventory views, recommendation views, and the approval UI the founder uses to review and approve/reject proposed actions before the execution engine (Phase 7) can act on them.

## Architecture

TBD when scoped. Must conform to [Engineering Handbook §6.1.3](../00_ENGINEERING_HANDBOOK.md#613-event-driven-processing) (long-running scan/analysis jobs observed via events, not blocking requests) and the UI/UX standards in the user-level rules (spacing, typography, color, component conventions).

## API changes

TBD when scoped. Expected: read endpoints for inventory/recommendations, write endpoint for approval decisions.

## Database changes

TBD when scoped. Expected: approval-decision records linked to recommendations.

## Folder changes

TBD when scoped. Populates `apps/frontend` and `packages/ui` beyond their current placeholder READMEs.

## Backend changes

TBD when scoped. Expected: approval-decision endpoint feeding the audit log.

## Frontend changes

TBD when scoped. This phase's primary deliverable.

## Security

TBD when scoped. Approval actions must be authenticated/authorized per the RBAC model from Phase 2 and audit-logged per [Handbook §13](../00_ENGINEERING_HANDBOOK.md#13-security-philosophy).

## Tests

TBD when scoped. Expected: first phase with meaningful e2e coverage (`tests/e2e`) — scan → recommendation → approval is a critical path per [Handbook §28](../00_ENGINEERING_HANDBOOK.md#28-testing-strategy).

## Manual checklist

- [ ] TBD when scoped.

## Definition of Done

- [ ] TBD when scoped.
