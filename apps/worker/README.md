# apps/worker

Background processing layer: storage scanning, intelligence/recommendation jobs, and execution-engine tasks that must not block the request/response cycle of `apps/backend`.

Event/queue-driven — consumes jobs enqueued by the backend, never receives direct HTTP traffic. Python + Celery, broker/result backend on Redis (ADR-005, ADR-012).

Phase 1 only proved the queue round-trip via `worker.health.ping`. 

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
celery -A worker.celery_app worker --loglevel=info
```

Requires `REDIS_URL` (see repo-root `.env.example`).

