# Phase 04 — Storage Intelligence

**Status:** ⬜ Not started — placeholder. To be expanded into a full spec by the CTO role before implementation begins, per [Engineering Handbook §27](../00_ENGINEERING_HANDBOOK.md#27-documentation-standards). Depends on Phase 3.

## Objective

Run analysis over the scanner's inventory: classification, duplicate/similarity detection, staleness signals — the non-AI-Gateway-dependent intelligence layer that Phase 5's recommendation engine will consume alongside AI Gateway output.

## Architecture

TBD when scoped. Must conform to [Engineering Handbook §8.6](../00_ENGINEERING_HANDBOOK.md#86-recommendation-engine) — this phase produces signals, not recommendations; it does not execute or propose actions itself.

## API changes

TBD when scoped.

## Database changes

TBD when scoped. Expected: derived-signal tables (duplicate groups, staleness scores, classification tags) linked to inventory records.

## Folder changes

TBD when scoped.

## Backend changes

TBD when scoped.

## Frontend changes

TBD when scoped. Expected: none.

## Security

TBD when scoped.

## Tests

TBD when scoped.

## Manual checklist

- [ ] TBD when scoped.

## Definition of Done

- [ ] TBD when scoped.
