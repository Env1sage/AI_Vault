from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from vault_shared.db.session import get_engine
from vault_shared.error_tracking import configure_sentry
from vault_shared.tracing import configure_tracing


def configure_observability(service_name: str) -> None:
    """Called once, before the FastAPI app is constructed — sets up the
    process-wide Sentry client and OTel tracer provider. Both are no-ops
    without `SENTRY_DSN`/`OTEL_EXPORTER_OTLP_ENDPOINT` set (Phase 10,
    ADR-022), so this is always safe to call."""
    configure_sentry(service_name, app_kind="fastapi")
    configure_tracing(service_name)


def instrument_app(app: FastAPI) -> None:
    """Called once, after the FastAPI app is constructed — wraps every
    route and every SQLAlchemy query with a span. A no-op in terms of
    exported data if `configure_observability` didn't install a real
    exporter, but still needs the app/engine instances to attach to."""
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=get_engine())
