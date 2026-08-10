# Phase 4 — Completion Report

**Phase:** [`PHASE_04_STORAGE_INTELLIGENCE.md`](PHASE_04_STORAGE_INTELLIGENCE.md) — Storage Discovery & Scanner Engine (filename is stale — see Technical Debt in the CTO Dashboard; the document's own content is the Storage Scanner, not intelligence/classification)
**Status:** Implemented by Claude. Awaiting founder manual test and CTO review (Engineering Handbook §4 lifecycle) before being marked complete in [`01_PROJECT_MASTER.md`](../01_PROJECT_MASTER.md).
**Date:** 2026-07-29

---

## 1. Read this first — two architectural decisions this phase required

**ADR-015 — `packages/shared` refactor.** Handbook §8.15 requires the scanner to run as a worker job, but through Phase 3 every DB model, repository, the DB session/engine, token encryption, and the Google Workspace OAuth client lived under `apps/backend/app/infrastructure/` — invisible to `apps/worker`'s separate venv. All of it moved to `packages/shared/vault_shared/*` so both apps import it identically. `ConnectorService` did **not** move wholesale: its `initiate_connect`/`complete_connect` depend on the backend-only, Redis-backed OAuth CSRF state (`oauth_state.py`), which has no meaning to a worker job. Only the token-refresh piece was extracted into a new `ConnectorTokenService` (`packages/shared/vault_shared/connector_service.py`); the backend's `ConnectorService` now composes it. See [ADR-015](../03_ARCHITECTURE_DECISIONS.md#adr-015-extract-dbsecurityconnector-code-from-appsbackend-into-packagesshared-ahead-of-phase-4) for the full reasoning. All 96 pre-existing backend tests and 18 pre-existing worker tests pass unchanged after the move.

**ADR-016 — Scanner design.** Three problems needed a resolved design before writing `ScannerService`: Google Drive's `files.list` gives no ordering guarantee (a folder can arrive after its own children), transient API failures must not fail a whole scan, and a running scan must be cancellable without killing the worker process. Resolved via: a **two-pass ingest** per source (stream-upsert with placeholder paths, then a bounded `_resolve_hierarchy` pass that re-reads just that source's folders from our own database to compute real materialized paths via a memoized parent-chain walk); **cooperative cancellation** via a `cancel_requested` column polled with a column-only query (not an entity fetch — an entity fetch can return a stale, identity-mapped object across the backend/worker process boundary); and **job-level retry** (Celery, 5 attempts, 30s backoff) on `DependencyUnavailableError`, safe because every write is an upsert. See [ADR-016](../03_ARCHITECTURE_DECISIONS.md#adr-016-storage-scanner-design--two-pass-hierarchy-resolution-cooperative-cancellation-job-level-retry) for full detail and alternatives considered.

## 2. Repository changes

```text
packages/shared/vault_shared/
  db/session.py                        moved from apps/backend/app/infrastructure/db/session.py
  db/models/
    audit_log.py, connector_credentials.py,          moved from apps/backend (imports rewritten,
    organization.py, refresh_token.py, role.py,        behavior unchanged)
    storage_connector.py, user.py
    storage_source.py                  NEW — StorageSource (+ DriveType: MY_DRIVE, SHARED_DRIVE)
    folder.py                          NEW — Folder (self-referential parent_folder_id, materialized path)
    file.py                            NEW — File (no content ever stored, metadata only)
    scan_job.py                        NEW — ScanJob (+ ScanType, ScanStatus), cancel_requested column
    scan_progress.py                   NEW — ScanProgress (one-to-one via shared PK, live counters)
    scan_event.py                      NEW — ScanEvent (append-only operational trail)
  db/repositories/
    audit_log_repository.py, connector_credentials_repository.py,   moved from apps/backend
    organization_repository.py, refresh_token_repository.py,
    role_repository.py, storage_connector_repository.py, user_repository.py
    storage_source_repository.py       NEW — get_by_connector_and_provider_drive_id, list_for_connector,
                                        upsert, update_change_token
    folder_repository.py               NEW — get_by_source_and_provider_id, upsert, count_for_source,
                                        delete_by_source_and_provider_id, list_for_source
    file_repository.py                 NEW — same shape as folder_repository.py
    scan_job_repository.py             NEW — create, get_by_id, list_for_connector, has_active_job,
                                        mark_running/completed/failed/cancelled, request_cancel,
                                        is_cancel_requested (column-only query, see ADR-016)
    scan_progress_repository.py        NEW — create_for_job, get_for_job, set_sources_discovered,
                                        set_current_source, increment_source_completed,
                                        increment_counts (atomic SET x = x + n)
    scan_event_repository.py           NEW — record, list_for_job (append-only)
  security/encryption.py               moved from apps/backend/app/infrastructure/security/encryption.py
  connectors/google_workspace.py       moved from apps/backend/app/infrastructure/connectors/
  connectors/google_drive.py           NEW — GoogleDriveClient: list_shared_drives, list_files_page,
                                        get_start_page_token, list_changes_page. Metadata-only field
                                        masks throughout — never fetches file content.
  connector_service.py                 NEW — ConnectorTokenService.get_valid_access_token (the extracted
                                        piece from ADR-015)

apps/backend/app/
  application/
    connector_service.py                REWRITTEN — composes ConnectorTokenService, keeps
                                         initiate_connect/complete_connect (oauth_state.py unchanged, stays)
    scan_service.py                     NEW — ScanService: list_for_connector, get_owned, get_progress,
                                         start_scan (validates CONNECTED + no-active-job, enqueues),
                                         cancel (validates PENDING/RUNNING)
  infrastructure/queue/scan_producer.py NEW — enqueue_scan_job(): a bare Celery client that calls
                                         .send_task("worker.scan.run", ...) by task-name string only —
                                         never imports worker code (apps stay independently deployable)
  presentation/
    api/v1/scans.py                     NEW — POST/GET /connectors/{id}/scans, GET /scans/{id},
                                         POST /scans/{id}/cancel
    api/v1/schemas.py                   + ScanJobResponse, ScanProgressResponse, StartScanRequest
    api/v1/router.py                    + scans_router
    dependencies/services.py            + get_scan_service
  alembic/versions/0004_scanner_tables.py   storage_sources, folders, files, scan_jobs, scan_events,
                                             scan_progress (full downgrade() included)
  requirements.txt                      + celery[redis] (backend needs the Celery *client* only)

apps/worker/worker/
  scanner/scan_service.py               NEW — ScannerService: run, _discover_sources, _scan_source,
                                         _ingest_full, _ingest_incremental, _ingest_item, _remove_item,
                                         _resolve_hierarchy, _check_cancelled; ScanCancelled exception
  tasks/scan.py                         NEW — worker.scan.run Celery task, retries on
                                         DependencyUnavailableError, marks job FAILED once retries exhaust
  celery_app.py                         + "worker.tasks.scan" in the include list

packages/types/src/scans.ts             NEW — ScanJob, ScanProgress, ScanType, ScanStatus, StartScanRequest
packages/types/src/index.ts             + scans.ts re-exports

apps/frontend/src/
  routes/scans.tsx                      NEW — current-scan progress (3s poll while active), last-successful-
                                         scan relative time, scan history, start/cancel actions, empty states
  routes/dashboard.tsx                   + "Scans" nav link
  lib/scan-status.ts (+ .test.ts)        scanStatusColor, isActiveScanStatus — pure, unit-tested
  lib/format-relative-time.ts (+ .test.ts)   formatRelativeTime(iso, now) — pure, unit-tested
                                         (`now` is an explicit param so tests don't need to mock the clock)

tests/unit/backend/test_scans_router.py            NEW — 13 tests (TestClient + dependency_overrides)
tests/integration/backend/test_scan_service_integration.py   NEW — 6 tests against real Postgres/Redis
tests/integration/worker/test_scan_service_integration.py    NEW — 4 tests against real Postgres
  (first-ever apps/worker integration tests — .github/workflows/ci.yml's worker job gained Postgres/Redis
  service containers + a migration step it didn't need before)
```

## 3. Database changes

Migration `0004_scanner_tables` (on top of Phase 3's `0003_storage_connectors`):

- **`storage_sources`** — one row per discoverable drive within a connected account ("My Drive" plus zero or more Shared Drives). Unique on `(connector_id, provider_drive_id)`. Carries `change_token` (Google's `startPageToken`), null until the first full scan completes.
- **`folders`** / **`files`** — provider-neutral inventory rows. Both unique on `(storage_source_id, provider_file_id)`, both have a self-referential-feeling `parent_folder_id` (folders: FK to `folders.id`; files: FK to `folders.id`) rebuilt from the provider's raw `provider_parent_id` at resolve time, and a materialized `path`. `files` additionally carries `mime_type`, `size_bytes`, `permissions_summary` (a simplified summary, not a full ACL mirror), `version_id`, `checksum`. **No file contents are ever stored** — explicit in both the model docstring and the phase spec's constraint.
- **`scan_jobs`** — one row per scan execution; `scan_type` (full/incremental), `status` (pending/running/completed/failed/cancelled), `cancel_requested` (cooperative cancellation flag), `error`, `started_at`/`completed_at`.
- **`scan_progress`** — one-to-one with `scan_jobs` via a shared primary key (`scan_job_id`), not extra columns on `scan_jobs` itself, since these counters update far more frequently than the job row and the frontend polls this specifically.
- **`scan_events`** — append-only operational trail (`scan_started`, `scan_cancelled`, `scan_failed`, `scan_completed`), distinct from `audit_logs` (which records only user-triggered lifecycle actions: `scan_started`, `scan_cancel_requested`).

All FKs cascade-delete. Verified via `alembic upgrade head --sql` (correct SQL) and `Base.metadata.tables.keys()` (all 13 tables across every phase register correctly).

## 4. API surface

```text
POST   /v1/connectors/{id}/scans            (owner/admin)                    → ScanJob (201)
GET    /v1/connectors/{id}/scans            (any authenticated org member)  → ScanJob[]
GET    /v1/scans/{id}                       (any authenticated org member)  → ScanJob (with progress)
POST   /v1/scans/{id}/cancel                (owner/admin)                    → ScanJob
```

`start_scan` rejects (409) if the connector isn't `CONNECTED` or a scan is already `PENDING`/`RUNNING` for it. `cancel` rejects (409) if the job isn't `PENDING`/`RUNNING`. All four endpoints 404 cleanly for a connector/job belonging to a different organization (same ownership-check pattern as Phase 3's connectors router). RBAC gating mirrors Phase 3: owner/admin for start/cancel, any org member for list/status — the phase spec didn't specify per-endpoint roles, so this follows the established Phase 3 precedent rather than inventing a new policy.

## 5. Worker behavior

`ScannerService.run(scan_job_id)`: loads the job and its connector, marks `RUNNING`, discovers every `StorageSource` (My Drive + each Shared Drive via `GoogleDriveClient.list_shared_drives`), then for each source runs a full scan (`files.list`, paginated, batch-committed every 200 items) or incremental scan (`changes.list` from the stored `startPageToken`, applying removals as deletes) depending on whether a `change_token` already exists. After ingest, `_resolve_hierarchy` re-reads that source's folders from the database and computes correct materialized paths regardless of the order items arrived in (see ADR-016). Cancellation is checked once per page fetch and once per source boundary. On success, `StorageConnector.last_synced_at` is stamped (the placeholder column Phase 3 left for exactly this) and the job marked `COMPLETED`; on `DependencyUnavailableError` the job is left `RUNNING` for the Celery task's own retry loop to handle; any other exception marks it `FAILED` immediately.

`worker.scan.run` (Celery task): `bind=True`, `max_retries=5`, 30s backoff. Retries only on `DependencyUnavailableError`; once retries are exhausted, the task itself marks the job `FAILED` (since `ScannerService.run()` deliberately did not). `ScanProgress` creation is guarded idempotent so a retried task re-entering `run()` for the same job doesn't collide on `scan_progress.scan_job_id`'s primary key.

## 6. Performance considerations

- **Streaming, not buffering.** Pages are processed and upserted immediately, batch-committed every 200 items (`_BATCH_COMMIT_SIZE`) — memory stays flat regardless of drive size, and a crash mid-scan loses at most one batch, not the whole scan.
- **Hierarchy resolution is bounded, not drive-sized.** `_resolve_hierarchy` only ever loads one source's *folders* into memory (a small subset of all items even at scale) — files are streamed through in a second pass using the already-resolved folder map, never held in memory as a batch.
- **Metadata-only field masks.** `GoogleDriveClient`'s `_FILE_FIELDS` constant restricts every Drive API response to metadata fields — content is never requested, let alone downloaded.
- **Atomic counters.** `ScanProgressRepository.increment_counts` uses a single `UPDATE ... SET x = x + n` rather than read-then-write, avoiding a race between the scanner's own batches and any other reader of that row.

## 7. Tests and what was actually verified in this environment

- **Backend:** 109 unit tests total (13 new for Phase 4's `/v1/scans` router, via `TestClient` + `dependency_overrides`, same pattern as Phase 3's connectors router tests) + 6 new integration tests (skip locally, run in CI against real Postgres/Redis: start/list/cancel lifecycle, active-job conflict, cross-org rejection, completed-job cancel rejection). `ruff`/`mypy` (via the repo's actual CI invocation, `--config-file packages/config/python/mypy.ini`) clean across 44 source files.
- **Worker:** 18 pre-existing unit tests unchanged + 4 new integration tests against a real Postgres (skip locally, run in CI — this is the **first** time `apps/worker` has integration tests at all, so `.github/workflows/ci.yml`'s worker job gained Postgres/Redis service containers and a migration step it never needed before): full scan producing correct materialized paths, hierarchy resolution when a child arrives before its parent in the same page (proving ingest order doesn't determine the final path), cancellation between sources stopping the scan cleanly, and a `DependencyUnavailableError` leaving the job `RUNNING` (not `FAILED`) for the Celery-level retry. All use a hand-written fake `GoogleDriveClient` — never a real Google API call. `ruff`/`mypy` clean across 7 source files.
- **Frontend:** 42 vitest tests total (2 new files — `scan-status.test.ts`, `format-relative-time.test.ts`). Consistent with Phase 1-3's established scope, `scans.tsx` itself is not unit-tested — covered by the founder's manual QA checklist instead. `eslint`/`tsc`/`vite build` all clean; `vite build` confirms `/scans` registers correctly in the generated route tree and its own JS chunk builds without error.
- **Live, not just mocked:** ran `vite build` + started the Vite dev server and confirmed `/` and `/scans` both serve the SPA shell without a build/runtime error.
- **Not verified in this environment:** the 6 new backend + 4 new worker integration tests against a live Postgres/Redis; a real scan against an actual Google Drive account (needs a connected Workspace connector from Phase 3); the full `docker compose up` stack; browser-rendered behavior of `/scans` against a real backend (this sandbox has no Docker daemon — same limitation noted in every prior phase's report). Say so explicitly rather than claiming full UI verification: the route was confirmed to build and its module graph to be free of import/type errors, not exercised end-to-end in a browser against live data.

**Concrete manual-test steps for the founder**, beyond Phase 1-3's checklist: with a Google Workspace connector already connected (Phase 3), run `docker compose up`, navigate to `/scans`, click "Start scan," confirm the current-status panel shows live progress (sources/folders/files counters incrementing, current source name) polling every few seconds while running; click "Cancel scan" mid-run and confirm it stops and shows `cancelled`; start a second scan and let it complete, confirm "Last successful scan" and the scan history list show it; disconnect network/revoke Drive access briefly during a scan to observe a retry-then-fail cycle if desired (optional, harder to stage deliberately).

## 8. Known limitations / follow-ups

- Same `packages/types` manual-sync caveat as prior phases (ADR-012), now also covering `scans.ts`.
- No live Postgres/Redis/Docker verification in this environment (cumulative gap since Phase 1) — see §7.
- A cancelled or job-retried scan can leave placeholder (pre-hierarchy-resolution) paths on a partially-scanned source until the next successful scan for that source — documented explicitly in ADR-016; Phase 5+ code reading `Folder`/`File.path` should treat a non-`COMPLETED` `ScanJob` as a signal inventory may be stale.
- Job-level retry re-does completed sources on a transient-failure retry rather than resuming mid-source — a deliberate simplification (ADR-016); upserts make it safe, just not maximally efficient for connectors with many large sources.
- `_resolve_hierarchy`'s recursive parent-chain walk relies on Python's default recursion limit — fine for realistic Drive folder depths, flagged as an accepted limitation rather than engineered around.
- Route components remain outside the automated test suite by consistent design choice (see §7) — standing item in the CTO Dashboard's Technical Debt.
- Phase roadmap numbering/filename mismatch (this phase's own doc is named `PHASE_04_STORAGE_INTELLIGENCE.md` but its content is the Storage Scanner) — left unresolved at the founder's standing instruction, noted in the CTO Dashboard.

## 9. Recommendation for Phase 5

Every `Folder`/`File` row now carries enough normalized metadata (mime type, size, owner, shared flag, checksum, timestamps, materialized path) for Phase 5's classification/duplicate-detection/staleness work to query directly — no additional scanner changes should be needed to support read-only analysis over this inventory. Phase 5 should treat a `ScanJob.status != "completed"` as a staleness signal for whatever source it covers (see §8) rather than assuming every row is current. If Phase 5 needs to trigger its own background jobs, follow this phase's queue-producer pattern (`apps/backend/app/infrastructure/queue/scan_producer.py`: enqueue by Celery task-name string only, never import worker code directly) rather than inventing a new mechanism.
