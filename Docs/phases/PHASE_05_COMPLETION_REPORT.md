# Phase 5 — Completion Report

**Phase:** [`PHASE_05_AI_INTELLIGENCE.md`](PHASE_05_AI_INTELLIGENCE.md) — Metadata Intelligence & Knowledge Engine (filename is stale — see Technical Debt in the CTO Dashboard; the document's own content is the deterministic Knowledge Engine, not the AI Gateway)
**Status:** Implemented by Claude. Awaiting founder manual test and CTO review (Engineering Handbook §4 lifecycle) before being marked complete in [`01_PROJECT_MASTER.md`](../01_PROJECT_MASTER.md).
**Date:** 2026-07-30

---

## 1. Read this first — the architectural decision this phase required

**ADR-017 — Knowledge Engine design.** The phase spec asks for a modular, deterministic-first enrichment pipeline (Handbook §8.3 Metadata Engine, §8.4 Knowledge Builder) over the Storage Scanner's inventory, explicitly *not* calling the AI Gateway, and explicitly leaving room for a future Embedding Engine without building one now. Four concrete design questions needed resolving: (1) enrichment lives entirely in `apps/worker` (mirroring the Scanner's split from Phase 4/ADR-015) — the backend only reads what the worker wrote; (2) Phase 4's scanner was deliberately metadata-only, so this phase adds the *first* real reads of file content, via new `GoogleDriveClient.download_file`/`export_file` methods (same `drive.readonly` scope already granted, no new consent); (3) classification and relationship discovery are scoped to a bounded, explainable set of rules rather than the spec's full literal wording (no fuzzy "similar naming"/"common folders" relationship types, no project/campaign inference) — an unbounded pairwise similarity graph is exactly what the phase's own "produce explainable outputs" principle warns against; (4) enrichment is auto-chained from every successful scan completion (Handbook §7's "scan-completed → metadata extracted" pipeline step), with a manual trigger also available for reprocessing. See [ADR-017](../03_ARCHITECTURE_DECISIONS.md#adr-017-knowledge-engine-phase-5--deterministic-first-pipeline-content-extraction-and-scanenrichment-chaining) for full reasoning and alternatives considered.

## 2. Repository changes

```text
packages/shared/vault_shared/
  db/models/
    file_metadata.py            NEW — FileMetadata (1:1 w/ File: normalized_extension, mime_type_validated,
                                 naming_pattern, version_label, owner_summary, sharing_summary,
                                 duplicate_group_key, language, enriched_at)
    file_classification.py      NEW — FileClassification (1:1 w/ File: document_type, confidence, method)
    file_extraction.py          NEW — FileExtraction (+ ExtractionStatus enum), 1:1 w/ File
    knowledge_attribute.py      NEW — KnowledgeAttribute (many per File: attribute_type/value/confidence/source)
    file_relationship.py        NEW — FileRelationship (+ RelationshipType enum), file_id/related_file_id edges
    enrichment_job.py           NEW — EnrichmentJob (+ EnrichmentJobStatus, EnrichmentTrigger), mirrors ScanJob
    enrichment_progress.py      NEW — EnrichmentProgress, mirrors ScanProgress
    enrichment_event.py         NEW — EnrichmentEvent, mirrors ScanEvent (append-only)
  db/repositories/
    file_metadata_repository.py, file_classification_repository.py,
    file_extraction_repository.py, knowledge_attribute_repository.py,
    file_relationship_repository.py, enrichment_job_repository.py,
    enrichment_progress_repository.py, enrichment_event_repository.py   NEW — one per model above
    file_repository.py          + get_owned_by_organization, list_by_ids, list_for_connector,
                                 count_for_connector, list_all_for_connector,
                                 list_pending_enrichment_for_connector, count_pending_enrichment_for_connector
  connectors/google_drive.py     + download_file (alt=media), export_file (Google-native Docs/Sheets/Slides)

apps/worker/worker/enrichment/
  naming.py                     NEW — detect_naming_pattern, extract_version_number, normalize_base_name
                                 (shared by NamingPatternAnalyzerProcessor and RelationshipDiscoveryService)
  extraction.py                 NEW — ContentExtractionService: PDF (pypdf), DOCX (python-docx),
                                 XLSX (openpyxl), PPTX (python-pptx), TXT/Markdown (plain decode),
                                 Google-native export (text/plain, text/csv). 20MB size cap,
                                 200,000-char output cap, control-character sanitization.
  processors.py                 NEW — FileProcessor protocol + 8 processors: ExtensionNormalizer,
                                 MimeValidator, FileTypeClassifier, FolderContextAnalyzer,
                                 NamingPatternAnalyzer, OwnershipAnalyzer, SharingAnalyzer,
                                 LanguageDetection. DEFAULT_PIPELINE list.
  relationships.py              NEW — RelationshipDiscoveryService: duplicate candidates (checksum),
                                 sequential versions (explicit version tokens, chronological fallback),
                                 shared ownership (same folder + owner) — chained pairs, bounded group size
  enrichment_service.py         NEW — EnrichmentService: run/_process_one_file/_enrich_file/
                                 _discover_relationships/_check_cancelled; EnrichmentCancelled exception

apps/worker/worker/tasks/
  enrichment.py                 NEW — worker.enrichment.run Celery task, same retry policy as worker.scan.run
  scan.py                       + _enqueue_enrichment_if_scan_completed (auto-chains after a completed scan)
  celery_app.py                 + "worker.tasks.enrichment" in the include list

apps/backend/app/
  application/
    file_service.py              NEW — FileService: list_for_connector, get_detail (assembles metadata/
                                  classification/extraction/knowledge attributes/related files)
    enrichment_job_service.py     NEW — EnrichmentJobService: list_for_connector, get_owned, get_progress,
                                  start (manual trigger), cancel — mirrors ScanService exactly
  infrastructure/queue/
    celery_client.py              NEW — shared lazy Celery client factory, extracted from scan_producer.py
    scan_producer.py               REWRITTEN to use celery_client.py (no behavior change)
    enrichment_producer.py        NEW — enqueue_enrichment_job, same task-name-string pattern as scans
  presentation/
    api/v1/files.py                NEW — GET /connectors/{id}/files, GET /files/{id}
    api/v1/enrichment.py            NEW — POST/GET /connectors/{id}/enrichment, GET/POST /enrichment/{id}(/cancel)
    api/v1/schemas.py               + FileSummaryResponse, FileListResponse, FileMetadataResponse,
                                    FileClassificationResponse, FileExtractionResponse,
                                    KnowledgeAttributeResponse, RelatedFileResponse, FileDetailResponse,
                                    EnrichmentProgressResponse, EnrichmentJobResponse
    api/v1/router.py                + enrichment_router, files_router
    dependencies/services.py        + get_enrichment_job_service, get_file_service
  alembic/versions/0005_knowledge_engine_tables.py   file_metadata, file_classifications, file_extractions,
                                    knowledge_attributes, file_relationships, enrichment_jobs,
                                    enrichment_progress, enrichment_events (full downgrade() included)

apps/worker/requirements.txt     + pypdf, python-docx, openpyxl, python-pptx (worker-only)

packages/types/src/files.ts, enrichment.ts   NEW — FileSummary, FileDetail, FileMetadata,
                                  FileClassification, FileExtractionInfo, KnowledgeAttribute, RelatedFile,
                                  EnrichmentJob, EnrichmentProgress
packages/types/src/index.ts       + re-exports

apps/frontend/src/
  routes/files.tsx                NEW — file browser (list, links to detail)
  routes/files.$fileId.tsx        NEW — file detail: metadata panel, classification, extraction status,
                                  knowledge attributes, related-files list
  routes/scans.tsx                + "Enrichment" section (status/progress, start/cancel), "Browse files" link
  routes/dashboard.tsx             + "Files" nav link
  lib/enrichment-status.ts (+ .test.ts)   enrichmentStatusColor, isActiveEnrichmentStatus — pure, unit-tested

tests/unit/backend/test_files_router.py, test_enrichment_router.py         NEW — 7 + 11 tests
tests/integration/backend/test_file_service_integration.py,
  test_enrichment_job_service_integration.py                               NEW — 5 + 6 tests, real Postgres/Redis
tests/unit/worker/test_naming.py, test_processors.py, test_extraction.py,
  test_relationships.py                                                    NEW — 43 tests total
tests/integration/worker/test_enrichment_service_integration.py            NEW — 6 tests, real Postgres
```

## 3. Database changes

Migration `0005_knowledge_engine_tables` (on top of Phase 4's `0004_scanner_tables`):

- **`file_metadata`** — 1:1 with `files` (shared PK `file_id`). Deterministic, structured facts a per-file processor contributed: normalized extension, MIME-validity flag (+ mismatch reason), naming pattern/version label, owner/sharing summaries, a nullable `duplicate_group_key` (set only by the relationship-discovery pass, never a per-file processor), detected language. `enriched_at` is what makes a file's "is this pending?" check possible.
- **`file_classifications`** — 1:1 with `files`. `document_type` + `confidence` + `method` (the exact rule name that fired, e.g. `keyword_invoice`, `mime_document_default`) — overwritten on re-enrichment, no history kept, since only the current classification is actionable.
- **`file_extractions`** — 1:1 with `files`. `status` (success/failed/unsupported/skipped_too_large), `extractor_name`, `extracted_text` (`Text`, sanitized + length-capped), `char_count`, `error`. This is the future Embedding Engine's input surface — deliberately never returned by the API's file-detail response (only status/size are), to keep payloads small.
- **`knowledge_attributes`** — many per file. Open-ended `(attribute_type, value, confidence, source)` shape (currently populated: `department`, `time_period`) rather than dedicated columns, so a future phase can add `project`/`campaign` without a migration. Unique on `(file_id, attribute_type, value)`; a reprocess replaces the whole set for a file (`KnowledgeAttributeRepository.replace_for_file`) rather than accumulating stale guesses.
- **`file_relationships`** — many rows, `file_id`/`related_file_id` directed edges with `relationship_type`, `confidence`, and a `metadata` JSONB explaining *why* (`match_reason`, or `owner_email` for shared-ownership edges). Unique on `(file_id, related_file_id, relationship_type)`. Denormalizes `connector_id` for cheap scoping/cleanup.
- **`enrichment_jobs`** / **`enrichment_progress`** / **`enrichment_events`** — mirror `scan_jobs`/`scan_progress`/`scan_events` exactly (same status lifecycle, same cooperative-cancellation column, same live-counters-in-a-separate-table reasoning). `enrichment_jobs.scan_job_id` (nullable, `ON DELETE SET NULL`) links a job back to the scan that triggered it, when applicable.

Verified via `alembic upgrade head --sql` (correct SQL) and `Base.metadata.tables.keys()` (all 21 tables across every phase register correctly).

## 4. API surface

```text
GET    /v1/connectors/{id}/files            (any authenticated org member)  → { items: FileSummary[], total }
GET    /v1/files/{id}                       (any authenticated org member)  → FileDetail (metadata, classification,
                                                                               extraction status, knowledge
                                                                               attributes, related files)
POST   /v1/connectors/{id}/enrichment       (owner/admin)                    → EnrichmentJob (201)
GET    /v1/connectors/{id}/enrichment       (any authenticated org member)  → EnrichmentJob[]
GET    /v1/enrichment/{id}                  (any authenticated org member)  → EnrichmentJob (with progress)
POST   /v1/enrichment/{id}/cancel           (owner/admin)                    → EnrichmentJob
```

`GET /v1/files/{id}` addresses a file directly (no connector id in the URL, unlike the scans/enrichment APIs), so ownership is checked via a join all the way to `storage_connectors.organization_id` (`FileRepository.get_owned_by_organization`) rather than a simple connector-id comparison. RBAC gating mirrors Phase 4's scans API exactly (owner/admin to start/cancel enrichment, any org member to read).

## 5. Worker behavior

`EnrichmentService.run(enrichment_job_id)`: loads the job and connector, marks `RUNNING`, queries `FileRepository.list_pending_enrichment_for_connector` — every `File` with no `FileMetadata` row yet, or whose `scanned_at` is newer than its `FileMetadata.enriched_at` — and for each: refreshes the connector's access token, runs `ContentExtractionService` (downloads/exports content only for a supported, size-bounded format; parsing failures are caught and recorded as a normal `FAILED` extraction, never raised), then runs every processor in `DEFAULT_PIPELINE` (a processor throwing is caught and skipped, logged, without affecting the others), merges their contributions, and persists `FileMetadata`/`FileClassification`/`KnowledgeAttribute` rows. After every file, a second pass (`_discover_relationships`) re-reads the connector's *entire* current file set (not just the ones just processed — a newly-enriched file can relate to an already-enriched sibling) and runs `RelationshipDiscoveryService`, persisting `FileRelationship` rows and back-filling `FileMetadata.duplicate_group_key` for checksum-matched groups.

Failure handling mirrors ADR-016's scanner exactly: a `DependencyUnavailableError`/`UnauthorizedError` (Drive connectivity/token problem — affects every remaining file identically) propagates to leave the job `RUNNING` for `worker.tasks.enrichment.run_enrichment`'s own Celery-level retry (5 attempts, 30s backoff); any other per-file exception is caught, the file is marked failed (`files_failed` incremented, an `EnrichmentEvent` recorded), and the job continues with the next file. Cancellation (`EnrichmentJob.cancel_requested`) is checked once per file and once before the relationship pass, via the same column-only-query pattern as the scanner.

`worker/tasks/scan.py`'s `_enqueue_enrichment_if_scan_completed` runs after every successful scan: it creates an `EnrichmentJob` (`triggered_by=SCAN_COMPLETED`, linked via `scan_job_id`) and calls `run_enrichment.delay(...)` directly — both tasks share one Celery app, so this is a plain in-process call, not a new message-bus abstraction. Skipped if an enrichment job is already active for that connector, or if the scan didn't complete successfully.

## 6. Performance considerations

- **Size- and length-bounded extraction.** A 20MB cap skips extraction outright for larger files; extracted text is capped at 200,000 characters after sanitization — no single file's content can grow a database row (or worker memory) without bound.
- **Bounded relationship discovery.** Groups (by folder+base-name, by checksum, by folder+owner) larger than 20 files are skipped entirely rather than truncated or fully cross-multiplied — O(n) chained edges per group, not O(n²) pairs, and no relationship row is ever a partial/misleading slice of a larger group.
- **Resumable "pending" query, not a snapshot.** Because pendency is computed live (`scanned_at > enriched_at` or no `FileMetadata` row), an interrupted job's next run — whether a retry or a fresh manual trigger — automatically picks up exactly what's still outstanding, with no separate touched-file bookkeeping to maintain or get out of sync.
- **Metadata-only Storage Scanner unchanged.** Phase 4's scanner still never reads file content; only this phase's `EnrichmentService`, running as its own job stage afterward, does — keeping the scan pass itself exactly as fast and lightweight as it was before this phase.

## 7. Tests and what was actually verified in this environment

- **Backend:** 127 unit tests total (18 new — `/v1/files` and `/v1/enrichment` routers via `TestClient` + `dependency_overrides`, same pattern as every prior router) + 11 new integration tests (skip locally, run in CI against real Postgres/Redis: `FileService` list/detail assembly including a real `FileRelationship` join, cross-org rejection; `EnrichmentJobService` start/list/get/cancel, active-job conflict). `ruff`/`mypy` (via the repo's actual CI invocation) clean across 51 source files.
- **Worker:** 43 new unit tests — `naming.py`'s pure functions; every one of the 8 per-file processors (including the invoice-keyword-does-NOT-override-an-image edge case, and the classifier's full fallback chain); all 6 extraction formats using real, freshly-generated DOCX/XLSX/PPTX files round-tripped through the actual libraries (not fixtures) plus a corrupt-PDF failure case and the Google-native export path; all 3 relationship types plus the group-size-cap boundary. Plus 6 new integration tests against a real Postgres (skip locally, run in CI): a full enrichment run persisting metadata/classification/extraction correctly, resumability across two consecutive runs (second run touches zero files), relationship discovery producing a real `sequential_version` edge, one file's unexpected failure not stopping a sibling file's success, `DependencyUnavailableError` leaving the job `RUNNING`, and cancellation. `ruff`/`mypy` clean across 14 source files.
- **Frontend:** 48 vitest tests total (6 new — `enrichment-status`). Consistent with every prior phase, `files.tsx`/`files.$fileId.tsx`/the updated `scans.tsx` are not unit-tested — covered by the founder's manual QA checklist. `eslint`/`tsc`/`vite build` all clean; `vite build` confirms `/files` and `/files/$fileId` register correctly in the generated route tree and build to their own JS chunks.
- **Live, not just mocked:** every extraction format was verified end-to-end against a real library round-trip (generate a DOCX/XLSX/PPTX/PDF in-memory with the actual authoring library, extract it back with `ContentExtractionService`, assert the text matches) — not just asserted against canned fixture bytes. `vite build` + a dev-server boot confirmed the new routes serve without a build/runtime error.
- **Not verified in this environment:** the 11 new backend + 6 new worker integration tests against a live Postgres/Redis; a real scan→enrich flow against an actual Google Drive account with real-world file content (needs a connected Workspace connector); the full `docker compose up` stack; browser-rendered behavior of `/files`/`/files/$fileId` against a real backend. Say so explicitly: extraction correctness was verified against libraries operating on well-formed, freshly-generated sample files, not the messier real-world documents a live account would contain.

**Concrete manual-test steps for the founder**, beyond Phase 1-4's checklist: with a connected Workspace connector and at least one completed scan, confirm an enrichment job auto-starts (visible on `/scans`'s new Enrichment section) without any manual action; once it completes, visit `/files`, open a few files, and confirm the metadata panel/classification/extraction status look reasonable for real files (PDFs, Google Docs, spreadsheets); check that a folder with genuinely versioned filenames (e.g. `Report_v1.docx`, `Report_v2.docx`) shows a "sequential version" relationship between them; click "Re-run enrichment" manually and confirm it completes quickly (nothing pending, since nothing changed).

## 8. Known limitations / follow-ups

- Same `packages/types` manual-sync caveat as prior phases (ADR-012), now also covering `files.ts`/`enrichment.ts`.
- No live Postgres/Redis/Docker verification in this environment (cumulative gap since Phase 1) — see §7.
- Relationship discovery is deliberately narrower than the phase spec's literal wording (no "common folders" or general "similar naming" relationship types) — documented explicitly in ADR-017 as a bounded-and-explainable scope cut, not an oversight.
- `project`/`campaign` knowledge attributes are not populated in this phase — only `department` and `time_period`. The phase spec's own example ("Campaign: Summer Launch") is explicitly deferred to the next phase's AI-assisted classification.
- A partially-enriched connector (job cancelled or failed mid-run) can leave some files with no `FileMetadata` yet, or stale relative to a later rescan — self-healing on the next enrichment run via the live "pending" query, not something that needs manual reconciliation.
- Job-level enrichment retry re-processes whatever the "pending" query returns at retry time (which may re-include files already handled in the failed attempt, since `FileMetadata.enriched_at` is only set at the very end of a file's processing) — safe because every write is an upsert, same accepted simplification ADR-016 made for the scanner.
- Route components remain outside the automated test suite by consistent design choice (see §7) — standing item in the CTO Dashboard's Technical Debt.
- Phase roadmap numbering/filename mismatch (this phase's content lives inside `PHASE_04_STORAGE_INTELLIGENCE.md`, alongside Phase 4's) — left unresolved at the founder's standing instruction, noted in the CTO Dashboard.

## 9. Recommendation for Phase 6

Every enriched file now carries a `FileClassification`, zero-or-more `KnowledgeAttribute`s, zero-or-more `FileRelationship` edges, and — where extraction succeeded — normalized text in `FileExtraction.extracted_text`, all with recorded confidence and an explaining `method`/`source`/`match_reason`. This is exactly the "priors to refine, not ground truth to replace" surface the next AI-layer phase should build on: an Embedding Engine can read `FileExtraction.extracted_text` directly (it's not exposed via the API on purpose — go through the repository); AI-assisted classification should treat this phase's deterministic `FileClassification`/`KnowledgeAttribute` rows as a fallback/prior to improve on rather than something to discard; and `project`/`campaign` inference (deferred here) is a natural first AI-assisted knowledge attribute to add. If the next phase needs its own background jobs, follow this phase's and Phase 4's queue-producer pattern (enqueue by Celery task-name string only, never import worker code directly) rather than inventing a new mechanism.
