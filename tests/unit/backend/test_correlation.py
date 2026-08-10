from app.infrastructure.queue.correlation import correlation_headers
from vault_shared import set_request_id


def test_empty_outside_a_request_context() -> None:
    set_request_id(None)
    assert correlation_headers() == {}


def test_carries_the_current_request_id_under_a_non_colliding_key() -> None:
    # Deliberately not "correlation_id" — that name collides with Celery's
    # own reserved AMQP property (always the task's own ID), see
    # correlation.py's docstring.
    set_request_id("req-abc-123")
    try:
        assert correlation_headers() == {"vault_request_id": "req-abc-123"}
    finally:
        set_request_id(None)
