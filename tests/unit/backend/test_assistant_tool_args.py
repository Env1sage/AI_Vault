import pytest
from app.application.assistant.registry import TOOL_REGISTRY
from app.application.assistant.tools import _clamp_int
from vault_shared import get_settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, 10),
        ("not a number", 10),
        (-5, 10),
        (0, 10),
        (5, 5),
        (100, 20),  # above maximum -> clamped to maximum, not the default
        ("7", 7),  # numeric strings coerce fine
    ],
)
def test_clamp_int(raw: object, expected: int) -> None:
    assert _clamp_int(raw, default=10, minimum=1, maximum=20) == expected


def test_clamp_int_minimum_zero_allows_zero() -> None:
    assert _clamp_int(0, default=10, minimum=0, maximum=20) == 0


@pytest.mark.parametrize("tool_name", sorted(TOOL_REGISTRY.keys()))
def test_every_tool_handler_signature_takes_context_and_args_only(tool_name: str) -> None:
    """Structural check on the security boundary: every handler's
    signature is `(ctx, args)` — organization/user identity can only come
    from `ctx`, never be smuggled in through `args`, because the handler
    has no other parameter it could read an id from."""
    import inspect

    handler = TOOL_REGISTRY[tool_name].handler
    params = list(inspect.signature(handler).parameters)
    assert params == ["ctx", "args"]


def test_every_registry_maximum_traces_to_a_settings_field() -> None:
    settings = get_settings()
    known_maxima = {
        settings.ai_max_context_items,
        settings.ai_max_search_results,
        settings.ai_max_large_file_threshold_bytes,
        settings.ai_max_age_days,
    }
    for spec in TOOL_REGISTRY.values():
        for arg_spec in spec.arg_schema.values():
            if arg_spec.maximum is not None:
                assert arg_spec.maximum in known_maxima, (
                    f"{spec.name}'s arg maximum {arg_spec.maximum!r} doesn't trace to any "
                    "Settings.ai_max_* field"
                )
