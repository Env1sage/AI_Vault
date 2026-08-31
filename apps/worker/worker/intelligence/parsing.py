import json
import re
from dataclasses import dataclass

# Matches a fenced code block, optionally tagged ```json, capturing only the
# inner content — some completion providers wrap JSON in markdown fences
# even when explicitly asked not to.
_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


class IntelligenceParseError(Exception):
    """Raised when a completion provider's response can't be turned into
    usable structured output — caught per-file by `IntelligenceService`,
    never a whole-job failure (the provider itself is reachable and
    responded; it's the *content* that's unusable, exactly like a
    malformed extraction is a per-file `FileExtraction` failure, not a
    whole-job one)."""


@dataclass(frozen=True)
class ParsedIntelligence:
    document_type: str | None
    summary: str | None
    entities: list[dict]
    structured_metadata: dict
    topics: list[str]
    confidence: float | None


def parse_response(text: str) -> ParsedIntelligence:
    """Strict on the outer shape (must be a single JSON object, or this
    raises), lenient on individual fields (a missing/malformed sub-field
    degrades to `None`/empty rather than failing the whole file) — the
    outer strictness is what makes a genuinely broken response
    (empty/truncated/prose-only) a clean, catchable failure; the per-field
    leniency is what keeps one odd field from discarding an otherwise-good
    extraction."""
    stripped = _strip_markdown_fences(text.strip())
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise IntelligenceParseError(f"Response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise IntelligenceParseError("Response JSON was not an object.")

    raw_metadata = data.get("structured_metadata")
    return ParsedIntelligence(
        document_type=_as_str_or_none(data.get("document_type")),
        summary=_as_str_or_none(data.get("summary")),
        entities=_as_list_of_dicts(data.get("entities")),
        structured_metadata=raw_metadata if isinstance(raw_metadata, dict) else {},
        topics=_as_list_of_strings(data.get("topics")),
        confidence=_as_confidence_or_none(data.get("confidence")),
    )


def _strip_markdown_fences(text: str) -> str:
    match = _FENCE_PATTERN.match(text)
    return match.group(1) if match else text


def _as_str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _as_list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _as_list_of_dicts(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _as_confidence_or_none(value: object) -> float | None:
    # Never fabricate a confidence value we couldn't parse — the same rule
    # this codebase already applies to OCR confidence (never a constant).
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    return max(0.0, min(1.0, float(value)))
