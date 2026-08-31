import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from vault_shared.db.repositories import DuplicateGroupRepository


@dataclass(frozen=True)
class SavingsSummary:
    duplicate_savings_bytes: int
    temporary_savings_bytes: int
    total_potential_savings_bytes: int


class SavingsAnalyzer:
    """Centralized savings calculation (Phase 1 spec §12) — combines the
    exact-duplicate-recoverable and temporary-candidate file sets by
    `file_id` set union before summing, never by adding each category's
    own total independently. A file that is both a redundant duplicate AND
    name-matches a temporary-file pattern is counted once, not twice."""

    def __init__(self, session: Session) -> None:
        self._duplicate_groups = DuplicateGroupRepository(session)

    def analyze(
        self, organization_id: uuid.UUID, *, temporary_candidate_sizes: dict[uuid.UUID, int]
    ) -> SavingsSummary:
        duplicate_sizes: dict[uuid.UUID, int] = dict(
            self._duplicate_groups.list_recoverable_file_ids_with_sizes_for_organization(
                organization_id
            )
        )
        duplicate_savings = sum(duplicate_sizes.values())

        # A file already counted as duplicate-recoverable contributes
        # nothing further even if it also matches a temporary-file
        # pattern — union, not addition.
        unique_temporary_ids = set(temporary_candidate_sizes) - set(duplicate_sizes)
        temporary_savings = sum(temporary_candidate_sizes[fid] for fid in unique_temporary_ids)

        return SavingsSummary(
            duplicate_savings_bytes=duplicate_savings,
            temporary_savings_bytes=temporary_savings,
            total_potential_savings_bytes=duplicate_savings + temporary_savings,
        )
