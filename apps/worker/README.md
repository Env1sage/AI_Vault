# apps/worker

Background processing layer: storage scanning, intelligence/recommendation jobs, and execution-engine tasks that must not block the request/response cycle of `apps/backend`.

Event/queue-driven — consumes jobs enqueued by the backend, never receives direct HTTP traffic. Python + Celery, broker/result backend on Redis (ADR-005, ADR-012).

Phase 1 only proved the queue round-trip via `worker.health.ping`. Phase 4 adds the first real business job: `worker.scan.run` (`worker/tasks/scan.py`), which invokes `ScannerService` (`worker/scanner/scan_service.py`) — a provider-agnostic, read-only traversal of every storage source a connector exposes, upserting `Folder`/`File` inventory rows via `packages/shared`'s DB layer. Retries up to 5 times (30s backoff) on transient Google API failures; supports cooperative cancellation via `ScanJob.cancel_requested`. See [`Docs/phases/PHASE_04_STORAGE_INTELLIGENCE.md`](../../Docs/phases/PHASE_04_STORAGE_INTELLIGENCE.md) and [ADR-016](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-016-storage-scanner-design--two-pass-hierarchy-resolution-cooperative-cancellation-job-level-retry) for the traversal/hierarchy-resolution/retry design, and [ADR-015](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-015-extract-dbsecurityconnector-code-from-appsbackend-into-packagesshared-ahead-of-phase-4) for why the worker can now import `vault_shared.db.*` at all.

Phase 5 adds the Knowledge Engine (`worker/enrichment/`): `worker.enrichment.run` (`worker/tasks/enrichment.py`) invokes `EnrichmentService` (`enrichment_service.py`), which runs ten deterministic per-file processors (`processors.py`) — extension/MIME/classification/folder-context/naming-pattern/ownership/sharing/language — plus a real Content Extraction Framework (`extraction.py`, PDF/DOCX/XLSX/PPTX/TXT/Markdown, and Google-native Docs/Sheets/Slides via Drive's `export` endpoint) and a bounded cross-file relationship pass (`relationships.py` — sequential versions, exact-checksum duplicate candidates, shared ownership). Auto-triggered after every successful scan (`worker/tasks/scan.py`'s completion chain) or manually via the backend's `/v1/connectors/{id}/enrichment`. Same job-level retry/cancellation shape as the scanner, plus per-file and per-processor failure isolation (one file's or one processor's failure never stops the rest of the job). See [ADR-017](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-017-knowledge-engine-phase-5--deterministic-first-pipeline-content-extraction-and-scanenrichment-chaining).

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
celery -A worker.celery_app worker --loglevel=info
```

Requires `REDIS_URL` (see repo-root `.env.example`).

