"""OpenTelemetry tracer-provider setup (Phase 10, ADR-022). Off by default —
mirrors the AI Gateway/email-provider "stub until real credentials exist"
pattern (Handbook §12): with no collector endpoint configured, OTel's own
default global TracerProvider is a no-op (near-zero overhead, spans are
created and immediately discarded), so every instrumentation call in this
codebase is always safe to make unconditionally. Setting
`OTEL_EXPORTER_OTLP_ENDPOINT` is the only thing that turns tracing on.
"""

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_tracing(service_name: str) -> None:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if not endpoint:
        return

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
