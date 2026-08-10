import uuid
from collections import defaultdict
from dataclasses import dataclass

from vault_shared.db.models import File, RelationshipType
from worker.enrichment.naming import extract_version_number, normalize_base_name

# Bounds how many files within one group (same folder, or same duplicate
# hash) get pairwise/chained relationships — an unusually large group (a
# huge shared folder, hundreds of files with the same owner) is exactly the
# case where a full graph would be noise, not signal. Groups above this size
# are skipped entirely rather than truncated, so a discovered relationship
# always reflects the *whole* group it came from.
_MAX_GROUP_SIZE = 20


@dataclass(frozen=True)
class DiscoveredRelationship:
    file_id: uuid.UUID
    related_file_id: uuid.UUID
    relationship_type: str
    confidence: float
    metadata: dict


class RelationshipDiscoveryService:
    """The Relationship Discovery pass (Phase 5 spec) — runs once per
    connector after every file has been individually processed, since every
    relationship type here requires comparing a file against its siblings
    (mirrors `ScannerService._resolve_hierarchy`'s "second pass over
    already-persisted rows" shape from Phase 4/ADR-016).

    Deliberately scoped to three explainable, high-precision relationship
    types rather than every dimension the phase spec lists ("common
    folders," "similar naming" in general) — an unbounded pairwise
    similarity graph over every file in a folder is exactly the kind of
    noisy, hard-to-explain output the phase's Design Principles ("produce
    explainable outputs") warn against. See ADR-017."""

    def discover(self, files: list[File]) -> list[DiscoveredRelationship]:
        discovered: list[DiscoveredRelationship] = []
        discovered.extend(self._duplicate_candidates(files))
        discovered.extend(self._sequential_versions(files))
        discovered.extend(self._shared_ownership(files))
        return discovered

    def _duplicate_candidates(self, files: list[File]) -> list[DiscoveredRelationship]:
        by_checksum: dict[str, list[File]] = defaultdict(list)
        for file in files:
            if file.checksum:
                by_checksum[file.checksum].append(file)

        results: list[DiscoveredRelationship] = []
        for group in by_checksum.values():
            if len(group) < 2 or len(group) > _MAX_GROUP_SIZE:
                continue
            for file, other in _consecutive_pairs(sorted(group, key=lambda f: f.name)):
                results.append(
                    DiscoveredRelationship(
                        file_id=file.id,
                        related_file_id=other.id,
                        relationship_type=RelationshipType.DUPLICATE_CANDIDATE,
                        confidence=0.95,
                        metadata={"match_reason": "identical_checksum"},
                    )
                )
        return results

    def _sequential_versions(self, files: list[File]) -> list[DiscoveredRelationship]:
        by_folder_and_base: dict[tuple[uuid.UUID | None, str], list[File]] = defaultdict(list)
        for file in files:
            base_name = normalize_base_name(file.name)
            by_folder_and_base[(file.parent_folder_id, base_name)].append(file)

        results: list[DiscoveredRelationship] = []
        for group in by_folder_and_base.values():
            if len(group) < 2 or len(group) > _MAX_GROUP_SIZE:
                continue

            versioned = [f for f in group if extract_version_number(f.name) is not None]
            if len(versioned) >= 2:
                ordered = sorted(versioned, key=lambda f: extract_version_number(f.name) or 0)
                confidence, reason = 0.85, "explicit_version_sequence"
            else:
                ordered = sorted(
                    group, key=lambda f: f.provider_modified_at or f.provider_created_at or f.name
                )
                confidence, reason = 0.5, "same_base_name_chronological"

            for file, other in _consecutive_pairs(ordered):
                results.append(
                    DiscoveredRelationship(
                        file_id=file.id,
                        related_file_id=other.id,
                        relationship_type=RelationshipType.SEQUENTIAL_VERSION,
                        confidence=confidence,
                        metadata={"match_reason": reason},
                    )
                )
        return results

    def _shared_ownership(self, files: list[File]) -> list[DiscoveredRelationship]:
        by_folder_and_owner: dict[tuple[uuid.UUID | None, str], list[File]] = defaultdict(list)
        for file in files:
            if file.owner_email:
                by_folder_and_owner[(file.parent_folder_id, file.owner_email)].append(file)

        results: list[DiscoveredRelationship] = []
        for (_, owner_email), group in by_folder_and_owner.items():
            if len(group) < 2 or len(group) > _MAX_GROUP_SIZE:
                continue
            ordered = sorted(group, key=lambda f: f.name)
            for file, other in _consecutive_pairs(ordered):
                results.append(
                    DiscoveredRelationship(
                        file_id=file.id,
                        related_file_id=other.id,
                        relationship_type=RelationshipType.SHARED_OWNERSHIP,
                        confidence=0.5,
                        metadata={"owner_email": owner_email},
                    )
                )
        return results


def _consecutive_pairs(ordered: list[File]) -> list[tuple[File, File]]:
    """Chains a sorted group into adjacent pairs rather than every
    combination — O(n) edges per group instead of O(n^2), and each edge is
    still individually explainable (Design Principles)."""
    return list(zip(ordered, ordered[1:], strict=False))
