import re
from dataclasses import dataclass
from typing import Any

_UUID_PATTERN = re.compile(
    r"\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b", re.IGNORECASE
)
_BYTES_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(kb|mb|gb|tb)\b", re.IGNORECASE)
_DAYS_PATTERN = re.compile(r"\b(a|an|\d+)\s*(day|week|month|year)s?\b", re.IGNORECASE)
_DAYS_PER_UNIT = {"day": 1, "week": 7, "month": 30, "year": 365}
_BYTES_PER_UNIT = {"kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, Any]


def _extract_bytes_threshold(question: str) -> int | None:
    match = _BYTES_PATTERN.search(question)
    if not match:
        return None
    return int(float(match.group(1)) * _BYTES_PER_UNIT[match.group(2).lower()])


def _extract_days(question: str) -> int | None:
    match = _DAYS_PATTERN.search(question)
    if not match:
        return None
    quantity = 1 if match.group(1).lower() in ("a", "an") else int(match.group(1))
    return quantity * _DAYS_PER_UNIT[match.group(2).lower()]


def _extract_uuid(question: str) -> str | None:
    match = _UUID_PATTERN.search(question)
    return match.group(1) if match else None


def _large_files(question: str) -> ToolCall:
    args: dict[str, Any] = {}
    threshold = _extract_bytes_threshold(question)
    if threshold is not None:
        args["min_size_bytes"] = threshold
    return ToolCall("get_large_files", args)


def _old_files(question: str) -> ToolCall:
    args: dict[str, Any] = {}
    days = _extract_days(question)
    if days is not None:
        args["older_than_days"] = days
    return ToolCall("get_old_files", args)


def _inactive_files(question: str) -> ToolCall:
    args: dict[str, Any] = {}
    days = _extract_days(question)
    if days is not None:
        args["inactive_days"] = days
    return ToolCall("get_inactive_files", args)


def _duplicate_group(question: str) -> ToolCall | None:
    group_id = _extract_uuid(question)
    if group_id is None:
        return None
    return ToolCall("get_duplicate_group", {"group_id": group_id})


def _duplicate_summary(_question: str) -> ToolCall:
    return ToolCall("get_duplicate_summary", {})


def _cleanup_candidates(_question: str) -> ToolCall:
    return ToolCall("get_cleanup_candidates", {})


def _storage_statistics(_question: str) -> ToolCall:
    return ToolCall("get_storage_statistics", {})


def _storage_overview(_question: str) -> ToolCall:
    return ToolCall("get_storage_overview", {})


def _search_files(question: str) -> ToolCall:
    return ToolCall("search_files", {"query": question})


# Ordered most-specific-first — the first matching rule wins. Each entry is
# (compiled pattern, extractor). A `None` return from the extractor (only
# possible for `_duplicate_group`, which requires a literal id) means "this
# pattern matched syntactically but didn't produce a usable call" — falls
# through to the next rule rather than emitting an empty/broken tool call.
_RULES: list[tuple[re.Pattern[str], Any]] = [
    (_UUID_PATTERN, _duplicate_group),
    (re.compile(r"duplicat", re.IGNORECASE), _duplicate_summary),
    (
        re.compile(r"\b(large|largest|biggest|huge|enormous)\b", re.IGNORECASE),
        _large_files,
    ),
    (
        re.compile(
            r"\b(old|oldest|stale)\b|haven'?t\s+been\s+(modified|touched|updated|edited)",
            re.IGNORECASE,
        ),
        _old_files,
    ),
    (
        re.compile(
            r"\b(inactive|unused|dormant)\b|nobody.*(opened|touched|used)|"
            r"haven'?t\s+been\s+(used|opened|accessed|viewed)",
            re.IGNORECASE,
        ),
        _inactive_files,
    ),
    (
        re.compile(
            r"clean\s*-?\s*up|cleanup|candidates?\s+for\s+(review|cleanup)|"
            r"what\s+should\s+i\s+(clean|review|delete)",
            re.IGNORECASE,
        ),
        _cleanup_candidates,
    ),
    (
        re.compile(
            r"break\s*down|statistics|composition|by\s+type|"
            r"(taking|consuming|using)\s+(up\s+)?(the\s+)?(most\s+)?(space|storage)",
            re.IGNORECASE,
        ),
        _storage_statistics,
    ),
    (
        re.compile(
            r"^(find|show me|where is|search for|look for|locate)\b.*"
            r"\b(presentation|document|report|spreadsheet|file|folder)\b|"
            r"related to|files? about|file called|files? for\b",
            re.IGNORECASE,
        ),
        _search_files,
    ),
    (
        re.compile(
            r"storage|disk\s+space|how\s+much.*(using|used|left)|recover|savings",
            re.IGNORECASE,
        ),
        _storage_overview,
    ),
]

# Fixed, deterministic multi-tool bundles — no model-driven/dynamic
# selection, just a second pattern that emits two calls when a compound
# question asks about both. Checked before the single-tool rules above.
_BUNDLE_RULES: list[tuple[re.Pattern[str], list[Any]]] = [
    (
        re.compile(
            r"(wast(e|ing)|recover|potential\s+savings).*\band\b.*"
            r"(clean\s*-?\s*up|cleanup|review)",
            re.IGNORECASE,
        ),
        [_storage_overview, _cleanup_candidates],
    ),
]


def classify_intent(question: str) -> list[ToolCall]:
    """Deterministic, keyword/regex-based intent routing (ADR-024) — not
    real LLM function-calling. Returns a list (possibly empty, meaning
    "fall through to the existing semantic-search RAG path") so a future
    smarter dispatcher can reuse the same call site without a rewrite;
    today only 0-2 entries are ever produced (single match, or one of the
    fixed bundle patterns below)."""
    for pattern, extractors in _BUNDLE_RULES:
        if pattern.search(question):
            return [extractor(question) for extractor in extractors]

    for pattern, extractor in _RULES:
        if pattern.search(question):
            call = extractor(question)
            if call is not None:
                return [call]

    return []
