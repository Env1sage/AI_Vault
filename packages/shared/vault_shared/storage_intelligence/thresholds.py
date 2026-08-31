"""Shared, named threshold constants for the Storage Intelligence Layer
(Phase 1) — imported by both the worker's batch counting logic
(`storage_analyzer.py`, `candidate_analyzer.py`) and the backend's API
layer (as query-param defaults), so a threshold never drifts between the
two call sites. All configurable per the spec ("do not hardcode a single
threshold throughout the codebase") via explicit function/query params;
these are only the defaults."""

LARGE_FILE_BYTES_DEFAULT = 100 * 1024 * 1024  # 100 MB — Phase 1 spec §8
OLD_FILE_DAYS_DEFAULT = 365  # Phase 1 spec §9 — "1+ year" is the headline bucket
INACTIVE_FILE_DAYS_DEFAULT = 365  # Phase 1 spec §10

# (label, inclusive lower bound bytes, exclusive upper bound bytes or None for open-ended)
SIZE_BUCKETS: list[tuple[str, int, int | None]] = [
    ("< 1 MB", 0, 1 * 1024 * 1024),
    ("1-10 MB", 1 * 1024 * 1024, 10 * 1024 * 1024),
    ("10-100 MB", 10 * 1024 * 1024, 100 * 1024 * 1024),
    ("100 MB-1 GB", 100 * 1024 * 1024, 1024 * 1024 * 1024),
    ("1-5 GB", 1024**3, 5 * 1024**3),
    ("> 5 GB", 5 * 1024**3, None),
]

# Old-file age buckets exposed by the Storage Analyzer summary (Phase 1
# spec §9 example: "Older than 1 year: 742 files").
OLD_FILE_AGE_BUCKET_DAYS: list[tuple[str, int]] = [
    ("30+ days", 30),
    ("90+ days", 90),
    ("180+ days", 180),
    ("1+ year", 365),
    ("2+ years", 730),
]

ACTIVE_WITHIN_DAYS = 30
RECENTLY_ACTIVE_WITHIN_DAYS = 180
