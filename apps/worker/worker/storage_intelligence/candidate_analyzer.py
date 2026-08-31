import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from vault_shared.db.models import File
from vault_shared.storage_intelligence.thresholds import (
    INACTIVE_FILE_DAYS_DEFAULT,
    LARGE_FILE_BYTES_DEFAULT,
    OLD_FILE_DAYS_DEFAULT,
)

# Same intent as `FileRepository.list_temporary_candidates_for_organization`'s
# SQL `ILIKE` patterns, expressed as Python regexes for the in-memory pass —
# kept as two independent implementations (SQL for live paginated browsing,
# regex for the batch job's counting/savings pass) rather than one shared
# abstraction, since the two need genuinely different forms.
_TEMPORARY_NAME_PATTERN = re.compile(
    r"(\.tmp$|\.temp$|\.cache$|\.log$|\.bak$|^~\$|copy|\(1\)|backup|\.old$)", re.IGNORECASE
)


@dataclass(frozen=True)
class CandidateSummary:
    large_file_count: int = 0
    large_file_bytes: int = 0
    old_file_count: int = 0
    old_file_bytes: int = 0
    inactive_file_count: int = 0
    inactive_file_bytes: int = 0
    temporary_candidate_count: int = 0
    temporary_candidate_bytes: int = 0
    temporary_candidate_sizes: dict[uuid.UUID, int] = field(default_factory=dict)


class CandidateAnalyzer:
    """Large/old/inactive/temporary-candidate counting for the persisted
    `StorageAnalysisSnapshot` — a single O(n) pass over the same
    already-fetched file list `StorageAnalyzer` uses (Phase 1 spec §8-11).
    Live, paginated *listing* of these same categories for browsing is a
    separate concern, served straight from indexed SQL queries on
    `FileRepository` (no need to persist per-file listings — see Phase 1
    audit note: "don't store calculated data unnecessarily if it can
    safely be derived"). Detection only — nothing here labels a file
    "unwanted" or "safe to delete" (Phase 1 spec §9.1, §11)."""

    def analyze(
        self,
        files: list[File],
        *,
        now: datetime | None = None,
        large_file_bytes: int = LARGE_FILE_BYTES_DEFAULT,
        old_file_days: int = OLD_FILE_DAYS_DEFAULT,
        inactive_file_days: int = INACTIVE_FILE_DAYS_DEFAULT,
    ) -> CandidateSummary:
        now = now or datetime.now(UTC)
        old_cutoff = now - timedelta(days=old_file_days)
        inactive_cutoff = now - timedelta(days=inactive_file_days)

        large_count = large_bytes = 0
        old_count = old_bytes = 0
        inactive_count = inactive_bytes = 0
        temp_count = temp_bytes = 0
        temp_sizes: dict[uuid.UUID, int] = {}

        for file in files:
            size = file.size_bytes or 0

            if size >= large_file_bytes:
                large_count += 1
                large_bytes += size

            if file.provider_modified_at is not None and file.provider_modified_at < old_cutoff:
                old_count += 1
                old_bytes += size

            last_activity = _last_activity(file)
            if last_activity is not None and last_activity < inactive_cutoff:
                inactive_count += 1
                inactive_bytes += size

            if _TEMPORARY_NAME_PATTERN.search(file.name):
                temp_count += 1
                temp_bytes += size
                temp_sizes[file.id] = size

        return CandidateSummary(
            large_file_count=large_count,
            large_file_bytes=large_bytes,
            old_file_count=old_count,
            old_file_bytes=old_bytes,
            inactive_file_count=inactive_count,
            inactive_file_bytes=inactive_bytes,
            temporary_candidate_count=temp_count,
            temporary_candidate_bytes=temp_bytes,
            temporary_candidate_sizes=temp_sizes,
        )


def _last_activity(file: File) -> datetime | None:
    candidates = [ts for ts in (file.provider_modified_at, file.provider_viewed_at) if ts]
    return max(candidates) if candidates else None
