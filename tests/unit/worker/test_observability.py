from types import SimpleNamespace

from vault_shared import get_request_id, get_task_id, set_request_id, set_task_id
from worker.observability import _record_task_finished, _record_task_start


def _task(name: str, request: object) -> SimpleNamespace:
    return SimpleNamespace(name=name, request=request)


def test_falls_back_to_the_task_id_when_no_correlation_header_was_sent() -> None:
    set_request_id(None)
    set_task_id(None)
    try:
        request = SimpleNamespace(vault_request_id=None)
        _record_task_start(task_id="task-1", task=_task("worker.health.ping", request))

        assert get_request_id() == "task-1"
        assert get_task_id() == "task-1"
    finally:
        set_request_id(None)
        set_task_id(None)


def test_uses_the_correlation_header_when_present_and_keeps_the_task_id_distinct() -> None:
    set_request_id(None)
    set_task_id(None)
    try:
        request = SimpleNamespace(vault_request_id="req-from-backend")
        _record_task_start(task_id="task-2", task=_task("worker.scan.run", request))

        assert get_request_id() == "req-from-backend"
        assert get_task_id() == "task-2"
    finally:
        set_request_id(None)
        set_task_id(None)


def test_clears_both_ids_after_the_task_finishes_so_a_reused_process_never_leaks_them() -> None:
    set_request_id("stale-request")
    set_task_id("stale-task")
    try:
        _record_task_finished(task_id="task-3", task=_task("worker.embedding.run", None), state="SUCCESS")

        assert get_request_id() is None
        assert get_task_id() is None
    finally:
        set_request_id(None)
        set_task_id(None)
