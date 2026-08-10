# Phase 03 — Storage Scanner

**Status:** ⬜ Not started — placeholder. To be expanded into a full spec by the CTO role before implementation begins, per [Engineering Handbook §27](../00_ENGINEERING_HANDBOOK.md#27-documentation-standards). Depends on Phase 1 and Phase 2.

## Objective

Build the Google Workspace `StorageConnector` implementation and the storage scanner that walks it into a normalized inventory (files, folders, metadata, permissions), read-only by construction.

## Architecture

TBD when scoped. Must conform to [Engineering Handbook §8.1-8.2](../00_ENGINEERING_HANDBOOK.md#81-storage-connector) (Storage Connector, Storage Scanner module cards) and §18 (Future Connector Architecture) — connector behind a provider-agnostic `StorageConnector` interface defined in `packages/types`, scanner runs in `apps/worker` per the Workers module (§8.15).

## API changes

TBD when scoped. Expected: endpoints to initiate/monitor a scan.

## Database changes

TBD when scoped. Expected: inventory schema (files/folders/metadata/permissions), scan-run/status tracking.

## Folder changes

TBD when scoped. Populates the Google Workspace connector under `apps/worker` (or a dedicated connector package — decide and record as an ADR if it changes the folder structure in Handbook §5).

## Backend changes

TBD when scoped. Expected: scan-trigger endpoints, job enqueue to `apps/worker`.

## Frontend changes

TBD when scoped. Expected: none — inventory viewing arrives Phase 6.

## Security

TBD when scoped. Must confirm: OAuth scope requested from Google is the narrowest that satisfies scanning (read-only), per [Handbook §13](../00_ENGINEERING_HANDBOOK.md#13-security-philosophy) least-privilege principle.

## Tests

TBD when scoped. Expected: integration tests against a mocked/sandboxed Google Workspace API.

## Manual checklist

- [ ] TBD when scoped.

## Definition of Done

- [ ] TBD when scoped.
