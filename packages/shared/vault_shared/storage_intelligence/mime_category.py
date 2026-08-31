"""Deterministic MIME-type → storage category classification (Phase 1 spec
§7.1: "use existing metadata first, do not unnecessarily invoke an LLM").
A pure lookup, not a model call — extensible by adding a prefix/exact-match
entry, exactly as the spec asks ("the classification system must be
extensible; future AI classification will improve this later"): a future
phase can override/augment this per-file without changing its shape."""

_EXACT_MATCHES: dict[str, str] = {
    "application/vnd.google-apps.folder": "Folders",
    "application/vnd.google-apps.document": "Documents",
    "application/vnd.google-apps.spreadsheet": "Spreadsheets",
    "application/vnd.google-apps.presentation": "Presentations",
    "application/vnd.google-apps.form": "Documents",
    "application/vnd.google-apps.drawing": "Images",
    "application/pdf": "Documents",
    "application/msword": "Documents",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Documents",
    "application/vnd.ms-excel": "Spreadsheets",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Spreadsheets",
    "application/vnd.ms-powerpoint": "Presentations",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "Presentations",
    "application/zip": "Archives",
    "application/x-zip-compressed": "Archives",
    "application/x-rar-compressed": "Archives",
    "application/x-7z-compressed": "Archives",
    "application/gzip": "Archives",
    "application/x-tar": "Archives",
    "application/json": "Code",
    "application/xml": "Code",
}

_PREFIX_MATCHES: list[tuple[str, str]] = [
    ("image/", "Images"),
    ("video/", "Videos"),
    ("audio/", "Audio"),
    ("text/x-", "Code"),
    ("text/", "Text"),
]


def classify_mime_category(mime_type: str | None) -> str:
    if not mime_type:
        return "Other"
    if mime_type in _EXACT_MATCHES:
        return _EXACT_MATCHES[mime_type]
    for prefix, category in _PREFIX_MATCHES:
        if mime_type.startswith(prefix):
            return category
    return "Other"


def size_bucket_for(size_bytes: int | None, buckets: list[tuple[str, int, int | None]]) -> str:
    if size_bytes is None:
        return "Unknown size"
    for label, lower, upper in buckets:
        if size_bytes >= lower and (upper is None or size_bytes < upper):
            return label
    return "Unknown size"
