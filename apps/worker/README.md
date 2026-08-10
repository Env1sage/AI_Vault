# apps/worker

Background processing layer: storage scanning, intelligence/recommendation jobs, and execution-engine tasks that must not block the request/response cycle of `apps/backend`.

Event/queue-driven — consumes jobs enqueued by the backend, never receives direct HTTP traffic. Python + Celery, broker/result backend on Redis (ADR-005, ADR-012).

Phase 1 only proved the queue round-trip via `worker.health.ping`. Phase 4 adds the first real business job: `worker.scan.run` (`worker/tasks/scan.py`), which invokes `ScannerService` (`worker/scanner/scan_service.py`) — a provider-agnostic, read-only traversal of every storage source a connector exposes, upserting `Folder`/`File` inventory rows via `packages/shared`'s DB layer. Retries up to 5 times (30s backoff) on transient Google API failures; supports cooperative cancellation via `ScanJob.cancel_requested`. See [`Docs/phases/PHASE_04_STORAGE_INTELLIGENCE.md`](../../Docs/phases/PHASE_04_STORAGE_INTELLIGENCE.md) and [ADR-016](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-016-storage-scanner-design--two-pass-hierarchy-resolution-cooperative-cancellation-job-level-retry) for the traversal/hierarchy-resolution/retry design, and [ADR-015](../../Docs/03_ARCHITECTURE_DECISIONS.md#adr-015-extract-dbsecurityconnector-code-from-appsbackend-into-packagesshared-ahead-of-phase-4) for why the worker can now import `vault_shared.db.*` at all.

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
celery -A worker.celery_app worker --loglevel=info
```

Requires `REDIS_URL` (see repo-root `.env.example`).

