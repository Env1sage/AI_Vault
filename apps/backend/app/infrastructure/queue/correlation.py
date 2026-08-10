from vault_shared import get_request_id


def correlation_headers() -> dict[str, str]:
    """Attaches the current HTTP request's ID to an enqueued Celery task
    (Phase 10, ADR-022) so the worker can log every line of that task's
    execution under the same `request_id` the backend logged the
    triggering API call under — the only way to grep "everything that
    happened because of this one request" across both services' logs.
    Empty outside a request context (there isn't always one — see
    `worker/observability.py`'s task_id fallback).

    Deliberately named `vault_request_id`, not `correlation_id` — Celery's
    own AMQP message protocol already reserves a `correlation_id` property
    (always the task's own ID, for RPC-style result matching), and
    `Context._get_custom_headers` strips any header whose key collides
    with one of Celery's own reserved `Context` attributes before the
    worker ever sees it. A custom header needs a name Celery doesn't
    already use."""
    request_id = get_request_id()
    return {"vault_request_id": request_id} if request_id else {}
