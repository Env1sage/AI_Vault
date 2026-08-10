import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
# Phase 10 (ADR-022) — distinct from request_id: a Celery task_id is always
# present in the worker (there's no originating HTTP request for a
# scheduler-fired or chained task), while request_id/correlation_id is only
# present when the task traces back to a real backend HTTP request.
_task_id_ctx: ContextVar[str | None] = ContextVar("task_id", default=None)

_RESERVED_LOG_RECORD_ATTRS = frozenset(logging.LogRecord(
    "", 0, "", 0, "", (), None,
).__dict__.keys())


def set_request_id(request_id: str | None) -> None:
    _request_id_ctx.set(request_id)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


def set_task_id(task_id: str | None) -> None:
    _task_id_ctx.set(task_id)


def get_task_id() -> str | None:
    return _task_id_ctx.get()


class JSONFormatter(logging.Formatter):
    """Structured JSON logging per Engineering Handbook §26 — never console.log,
    secrets/PII must never be passed as log fields by callers."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = get_request_id()
        if request_id:
            payload["request_id"] = request_id

        task_id = get_task_id()
        if task_id:
            payload["task_id"] = task_id

        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_ATTRS and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(service_name: str, level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)

    logging.getLogger(service_name)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
