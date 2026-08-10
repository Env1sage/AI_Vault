import json
import logging

from vault_shared.logging import (
    JSONFormatter,
    get_request_id,
    get_task_id,
    set_request_id,
    set_task_id,
)


def _make_record(message: str = "hello", **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formats_record_as_valid_json_with_expected_fields() -> None:
    formatter = JSONFormatter()
    record = _make_record("hello world")

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "hello world"
    assert payload["level"] == "info"
    assert payload["logger"] == "test.logger"
    assert "timestamp" in payload


def test_includes_request_id_when_set() -> None:
    set_request_id("req-123")
    try:
        formatter = JSONFormatter()
        payload = json.loads(formatter.format(_make_record()))
        assert payload["request_id"] == "req-123"
    finally:
        set_request_id(None)


def test_omits_request_id_when_not_set() -> None:
    set_request_id(None)
    formatter = JSONFormatter()
    payload = json.loads(formatter.format(_make_record()))
    assert "request_id" not in payload


def test_get_request_id_reflects_set_request_id() -> None:
    set_request_id("abc")
    assert get_request_id() == "abc"
    set_request_id(None)
    assert get_request_id() is None


def test_includes_task_id_when_set() -> None:
    set_task_id("task-456")
    try:
        formatter = JSONFormatter()
        payload = json.loads(formatter.format(_make_record()))
        assert payload["task_id"] == "task-456"
    finally:
        set_task_id(None)


def test_omits_task_id_when_not_set() -> None:
    set_task_id(None)
    formatter = JSONFormatter()
    payload = json.loads(formatter.format(_make_record()))
    assert "task_id" not in payload


def test_get_task_id_reflects_set_task_id() -> None:
    set_task_id("xyz")
    assert get_task_id() == "xyz"
    set_task_id(None)
    assert get_task_id() is None


def test_extra_fields_are_included_without_leaking_reserved_attrs() -> None:
    formatter = JSONFormatter()
    payload = json.loads(formatter.format(_make_record(http_method="GET", status_code=200)))

    assert payload["http_method"] == "GET"
    assert payload["status_code"] == 200
    assert "pathname" not in payload
    assert "msg" not in payload
