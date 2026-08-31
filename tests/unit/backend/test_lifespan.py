"""Covers the search-performance fix in `app.main._lifespan`: the AI
Gateway's embedding provider must be warmed once at process startup, off
the request path, instead of lazily inside whichever search/chat request
happens to arrive first (measured at 80-170s of blocking model-load time
against the real backend — see the search performance diagnostic)."""

import asyncio
from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from app.main import _lifespan


def _run_lifespan_once(fake_gateway: MagicMock) -> None:
    async def _drive() -> None:
        async with _lifespan(FastAPI()):
            pass

    with (
        patch("app.main.get_ai_gateway", return_value=fake_gateway),
        patch("app.main.get_engine"),
        patch("app.main.get_redis"),
    ):
        asyncio.run(_drive())


def test_lifespan_warms_the_ai_gateway_before_yielding() -> None:
    fake_gateway = MagicMock()

    _run_lifespan_once(fake_gateway)

    # By the time startup has yielded (the app is "ready"), the gateway
    # must already have been warmed — not deferred to the first real
    # request.
    fake_gateway.embed.assert_called_once()


def test_lifespan_does_not_fail_startup_if_the_warmup_call_fails() -> None:
    """Search/chat aren't the only things this API serves — a broken or
    slow embedding provider must never take down connectors/scans/files/etc,
    so a warmup failure is swallowed, not raised."""
    fake_gateway = MagicMock()
    fake_gateway.embed.side_effect = RuntimeError("model load failed")

    _run_lifespan_once(fake_gateway)  # must not raise
