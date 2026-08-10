import re

# Shared by `NamingPatternAnalyzerProcessor` (per-file metadata) and
# `RelationshipDiscoveryService` (cross-file version-sequence grouping) —
# factored out so both use the exact same notion of "what a version token
# looks like" rather than two regexes that could quietly drift apart.
_VERSION_RE = re.compile(r"(?:^|[_\-\s(])v(\d+)(?:[_\-\s).]|$)", re.IGNORECASE)
_FINAL_RE = re.compile(r"final", re.IGNORECASE)
_DRAFT_RE = re.compile(r"draft", re.IGNORECASE)
_STRIP_RE = re.compile(r"[_\-\s]*(?:v\d+|final|draft)[_\-\s]*", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")

# A handful of Drive files have no real title and fall back to a content
# excerpt as their `name` (seen in the wild against a real account) — a
# naive "everything after the last dot" split can then grab a whole
# sentence fragment as the "extension", which is both meaningless and long
# enough to overflow `file_metadata.normalized_extension` (String(50)).
# Real extensions are short and have no whitespace, so anything outside
# that shape is treated as "no extension" rather than truncated garbage.
_MAX_PLAUSIBLE_EXTENSION_LENGTH = 15


def detect_naming_pattern(name: str) -> tuple[str, str | None]:
    """Returns (naming_pattern, version_label) — e.g. ("versioned", "v2"),
    ("final", "final"), ("plain", None)."""
    match = _VERSION_RE.search(name)
    if match:
        return "versioned", f"v{match.group(1)}"
    if _FINAL_RE.search(name):
        return "final", "final"
    if _DRAFT_RE.search(name):
        return "draft", "draft"
    return "plain", None


def extract_version_number(name: str) -> int | None:
    match = _VERSION_RE.search(name)
    return int(match.group(1)) if match else None


def extract_plausible_extension(name: str) -> str | None:
    """Returns the lowercased text after the last "." — but only if it's
    shaped like a real file extension (short, no whitespace). Anything
    else (a sentence fragment some Drive files fall back to as a "name")
    is treated as no extension at all."""
    if "." not in name:
        return None
    candidate = name.rsplit(".", 1)[-1].lower()
    if not candidate or len(candidate) > _MAX_PLAUSIBLE_EXTENSION_LENGTH or " " in candidate:
        return None
    return candidate


def normalize_base_name(name: str) -> str:
    """Strips the extension and any version/final/draft token, for grouping
    files that are otherwise "the same document" — e.g. "Report_v1.docx"
    and "Report_v2.docx" both normalize to "report"."""
    stem = name.rsplit(".", 1)[0] if "." in name else name
    stripped = _STRIP_RE.sub(" ", stem)
    return _WHITESPACE_RE.sub(" ", stripped).strip().lower()
