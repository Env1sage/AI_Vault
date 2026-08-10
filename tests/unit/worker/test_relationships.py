import uuid
from datetime import UTC, datetime

from vault_shared.db.models import File, RelationshipType
from worker.enrichment.relationships import RelationshipDiscoveryService


def _make_file(
    *,
    name: str,
    checksum: str | None = None,
    owner_email: str | None = None,
    parent_folder_id: uuid.UUID | None = None,
    modified: datetime | None = None,
) -> File:
    file = File(storage_source_id=uuid.uuid4(), provider_file_id=str(uuid.uuid4()))
    file.id = uuid.uuid4()
    file.name = name
    file.checksum = checksum
    file.owner_email = owner_email
    file.parent_folder_id = parent_folder_id
    file.provider_modified_at = modified
    file.provider_created_at = modified
    return file


def test_discovers_duplicate_candidates_by_identical_checksum() -> None:
    folder = uuid.uuid4()
    original = _make_file(name="Logo.png", checksum="abc123", parent_folder_id=folder)
    copy = _make_file(name="Logo_copy.png", checksum="abc123", parent_folder_id=folder)

    relationships = RelationshipDiscoveryService().discover([original, copy])

    duplicates = [r for r in relationships if r.relationship_type == RelationshipType.DUPLICATE_CANDIDATE]
    assert len(duplicates) == 1
    assert duplicates[0].confidence == 0.95
    assert duplicates[0].metadata == {"match_reason": "identical_checksum"}


def test_does_not_flag_files_with_different_checksums_as_duplicates() -> None:
    folder = uuid.uuid4()
    a = _make_file(name="a.png", checksum="aaa", parent_folder_id=folder)
    b = _make_file(name="b.png", checksum="bbb", parent_folder_id=folder)

    relationships = RelationshipDiscoveryService().discover([a, b])

    assert not any(r.relationship_type == RelationshipType.DUPLICATE_CANDIDATE for r in relationships)


def test_discovers_an_explicit_version_sequence() -> None:
    folder = uuid.uuid4()
    v1 = _make_file(name="Report_v1.docx", parent_folder_id=folder)
    v2 = _make_file(name="Report_v2.docx", parent_folder_id=folder)

    relationships = RelationshipDiscoveryService().discover([v2, v1])  # order shouldn't matter

    versions = [r for r in relationships if r.relationship_type == RelationshipType.SEQUENTIAL_VERSION]
    assert len(versions) == 1
    assert versions[0].file_id == v1.id
    assert versions[0].related_file_id == v2.id
    assert versions[0].confidence == 0.85
    assert versions[0].metadata == {"match_reason": "explicit_version_sequence"}


def test_falls_back_to_chronological_ordering_without_explicit_versions() -> None:
    folder = uuid.uuid4()
    older = _make_file(
        name="Report_draft.docx", parent_folder_id=folder, modified=datetime(2026, 1, 1, tzinfo=UTC)
    )
    newer = _make_file(
        name="Report_final.docx", parent_folder_id=folder, modified=datetime(2026, 2, 1, tzinfo=UTC)
    )

    relationships = RelationshipDiscoveryService().discover([newer, older])

    versions = [r for r in relationships if r.relationship_type == RelationshipType.SEQUENTIAL_VERSION]
    assert len(versions) == 1
    assert versions[0].confidence == 0.5
    assert versions[0].metadata == {"match_reason": "same_base_name_chronological"}


def test_discovers_shared_ownership_within_a_folder() -> None:
    folder = uuid.uuid4()
    a = _make_file(name="a.docx", owner_email="ada@acme.com", parent_folder_id=folder)
    b = _make_file(name="b.docx", owner_email="ada@acme.com", parent_folder_id=folder)

    relationships = RelationshipDiscoveryService().discover([a, b])

    shared = [r for r in relationships if r.relationship_type == RelationshipType.SHARED_OWNERSHIP]
    assert len(shared) == 1
    assert shared[0].metadata == {"owner_email": "ada@acme.com"}


def test_does_not_link_files_with_different_owners() -> None:
    folder = uuid.uuid4()
    a = _make_file(name="a.docx", owner_email="ada@acme.com", parent_folder_id=folder)
    b = _make_file(name="b.docx", owner_email="bob@acme.com", parent_folder_id=folder)

    relationships = RelationshipDiscoveryService().discover([a, b])

    assert not any(r.relationship_type == RelationshipType.SHARED_OWNERSHIP for r in relationships)


def test_skips_groups_larger_than_the_bound() -> None:
    folder = uuid.uuid4()
    files = [
        _make_file(name=f"file{i}.png", checksum="same", parent_folder_id=folder) for i in range(25)
    ]

    relationships = RelationshipDiscoveryService().discover(files)

    assert not any(r.relationship_type == RelationshipType.DUPLICATE_CANDIDATE for r in relationships)
