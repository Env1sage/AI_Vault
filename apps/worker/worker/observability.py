"""Celery-side observability (Phase 10, ADR-022) — imported once for its
side effects (registers the signal handlers below) by `celery_app.py`.
Mirrors the backend's `app/core/metrics_middleware.py`: one counter/
histogram observation per task, using the task name as the label (never a
task argument — same unbounded-cardinality rule as the backend's route
labels).
"""

import time

from celery.signals import task_postrun, task_prerun

from vault_shared import set_request_id, set_task_id
from vault_shared.metrics import record_celery_task

_task_started_at: dict[str, float] = {}


@task_prerun.connect
def _record_task_start(task_id: str, task: object, **_: object) -> None:
    _task_started_at[task_id] = time.perf_counter()

    # Correlation IDs (Phase 10, ADR-022) — every worker log line for this
    # task now carries the same request_id the backend logged the
    # triggering HTTP call under, via `app/infrastructure/queue/
    # correlation.py`'s `vault_request_id` header (deliberately not
    # `correlation_id` — that name collides with Celery's own reserved
    # AMQP property, always equal to the task's own ID, and gets stripped
    # before it would ever reach `request.headers`; see that module's
    # docstring). Falls back to this task's own Celery ID when there
    # wasn't an originating HTTP request (a scheduler-fired trigger, or
    # one worker task chaining into another) — every log line is always
    # attributable to *something*, never blank.
    request = getattr(task, "request", None)
    correlation_id = getattr(request, "vault_request_id", None)
    set_request_id(correlation_id or task_id)
    set_task_id(task_id)


@task_postrun.connect
def _record_task_finished(task_id: str, task: object, state: str, **_: object) -> None:
    # `state` is already the task's terminal status (SUCCESS/FAILURE/RETRY/
    # ...) — task_postrun fires exactly once per task regardless of
    # outcome, so this is the only signal handler needed; pairing it with
    # `task_failure` would double-count failed tasks.
    started_at = _task_started_at.pop(task_id, None)
    duration_seconds = time.perf_counter() - started_at if started_at is not None else 0.0
    task_name = getattr(task, "name", "unknown")
    record_celery_task(task_name, state.lower(), duration_seconds)

    # A prefork child reuses the same process (and the same contextvars)
    # across many tasks — clear both so an unrelated later task never
    # inherits this one's IDs in its logs.
    set_request_id(None)
    set_task_id(None)
