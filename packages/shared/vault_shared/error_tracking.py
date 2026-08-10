"""Sentry (or equivalent) error tracking (Phase 10, ADR-022). Off by
default, same stub-until-configured pattern as `tracing.py` — with no DSN,
`sentry_sdk.init` is simply never called, so every call site stays a
harmless no-op rather than needing its own `if sentry_configured` guard.
"""

import os
from typing import Literal

import sentry_sdk
from sentry_sdk.integrations import Integration

from vault_shared.settings import get_settings


def configure_sentry(service_name: str, *, app_kind: Literal["fastapi", "celery"]) -> None:
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        return

    settings = get_settings()
    integrations: list[Integration] = []
    if app_kind == "fastapi":
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        integrations = [StarletteIntegration(), FastApiIntegration()]
    else:
        from sentry_sdk.integrations.celery import CeleryIntegration

        integrations = [CeleryIntegration()]

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.environment,
        server_name=service_name,
        integrations=integrations,
        traces_sample_rate=0.1,
        # Never send request bodies/user PII to a third-party service by
        # default (Handbook §13) — a founder who wants richer Sentry
        # context can opt in later at the Sentry-project level, not here.
        send_default_pii=False,
    )
