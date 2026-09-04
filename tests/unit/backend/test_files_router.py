import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.main import app
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_file_service
from fastapi.testclient import TestClient
from vault_shared import NotFoundError

client = TestClient(app)


class _FakeFile:
    def __init__(self, *, name: str = "Report.pdf") -> None:
        self.id = uuid.uuid4()
        self.name = name
        self.path = f"/Finance/{name}"
        self.mime_type = "application/pdf"
        self.size_bytes = 2048
        self.is_shared = False
        self.owner_email = "founder@acme.com"
        self.provider_modified_at = datetime.now(UTC)
        self.web_view_link = f"https://drive.google.com/file/d/{self.id}/view"


class _FakeFileMetadata:
    def __init__(self) -> None:
        self.normalized_extension = "pdf"
        self.mime_type_validated = True
        self.mime_mismatch_reason = None
        self.naming_pattern = "plain"
        self.version_label = None
        self.owner_summary = "founder@acme.com"
        self.sharing_summary = "private"
        self.duplicate_group_key = None
        self.language = "en"
        self.enriched_at = datetime.now(UTC)


class _FakeFileClassification:
    def __init__(self) -> None:
        self.document_type = "Documentation"
        self.confidence = 0.5
        self.method = "mime_document_default"
        self.classified_at = datetime.now(UTC)


class _FakeFileExtraction:
    def __init__(self) -> None:
        self.status = "success"
        self.extractor_name = "pdf"
        self.char_count = 120
        self.error = None
        self.extracted_at = datetime.now(UTC)


class _FakeFileIntelligence:
    def __init__(self) -> None:
        self.status = "success"
        self.document_type = "contract"
        self.summary = "A services agreement between two parties."
        self.entities = [{"type": "party", "value": "Acme Corp", "confidence": 0.9}]
        self.structured_metadata = {"effective_date": "2026-01-01"}
        self.topics = ["services"]
        self.confidence = 0.87
        self.provider = "openai_compatible"
        self.model_name = "kimi-k2-0711-preview"
        self.error = None
        self.processed_at = datetime.now(UTC)


class _FakeKnowledgeAttribute:
    def __init__(self, *, attribute_type: str, value: str) -> None:
        self.attribute_type = attribute_type
        self.value = value
        self.confidence = 0.6
        self.source = "folder_context_analyzer"


@dataclass
class _FakeFileRelationshipRow:
    file_id: uuid.UUID
    related_file_id: uuid.UUID
    relationship_type: str = "sequential_version"
    confidence: float = 0.85
    metadata_: dict = field(default_factory=dict)


@dataclass
class _FakeRelatedFile:
    file: _FakeFile
    relationship: _FakeFileRelationshipRow


@dataclass
class _FakeFileDetail:
    file: _FakeFile
    metadata: _FakeFileMetadata | None
    classification: _FakeFileClassification | None
    extraction: _FakeFileExtraction | None
    intelligence: _FakeFileIntelligence | None
    knowledge_attributes: list
    related_files: list


@pytest.fixture
def fake_file_service() -> MagicMock:
    service = MagicMock()
    app.dependency_overrides[get_file_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_file_service, None)


@pytest.fixture
def as_member(member_user):
    app.dependency_overrides[get_current_user] = lambda: member_user
    yield member_user
    app.dependency_overrides.pop(get_current_user, None)


def test_list_files_requires_authentication(fake_file_service) -> None:
    response = client.get(f"/v1/connectors/{uuid.uuid4()}/files")
    assert response.status_code == 401


def test_list_files_returns_a_paginated_envelope(as_member, fake_file_service) -> None:
    fake_file_service.list_for_connector.return_value = ([_FakeFile()], 1)

    response = client.get(f"/v1/connectors/{uuid.uuid4()}/files")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "Report.pdf"


def test_list_files_returns_not_found_for_another_organizations_connector(
    as_member, fake_file_service
) -> None:
    fake_file_service.list_for_connector.side_effect = NotFoundError("Connector not found.")

    response = client.get(f"/v1/connectors/{uuid.uuid4()}/files")

    assert response.status_code == 404


def test_get_file_detail_requires_authentication(fake_file_service) -> None:
    response = client.get(f"/v1/files/{uuid.uuid4()}")
    assert response.status_code == 401


def test_get_file_detail_returns_the_full_enrichment_picture(as_member, fake_file_service) -> None:
    file = _FakeFile()
    related_file = _FakeFile(name="Report_v1.pdf")
    detail = _FakeFileDetail(
        file=file,
        metadata=_FakeFileMetadata(),
        classification=_FakeFileClassification(),
        extraction=_FakeFileExtraction(),
        intelligence=_FakeFileIntelligence(),
        knowledge_attributes=[_FakeKnowledgeAttribute(attribute_type="department", value="Finance")],
        related_files=[
            _FakeRelatedFile(
                file=related_file,
                relationship=_FakeFileRelationshipRow(
                    file_id=file.id, related_file_id=related_file.id
                ),
            )
        ],
    )
    fake_file_service.get_detail.return_value = detail

    response = client.get(f"/v1/files/{file.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Report.pdf"
    assert body["web_view_link"] == file.web_view_link
    assert body["metadata"]["normalized_extension"] == "pdf"
    assert body["classification"]["document_type"] == "Documentation"
    assert body["extraction"]["status"] == "success"
    assert body["intelligence"]["document_type"] == "contract"
    assert body["intelligence"]["summary"] == "A services agreement between two parties."
    assert body["intelligence"]["entities"][0]["value"] == "Acme Corp"
    assert body["knowledge_attributes"][0]["attribute_type"] == "department"
    assert body["related_files"][0]["name"] == "Report_v1.pdf"
    assert body["related_files"][0]["relationship_type"] == "sequential_version"


def test_get_file_detail_returns_not_found_for_another_organizations_file(
    as_member, fake_file_service
) -> None:
    fake_file_service.get_detail.side_effect = NotFoundError("File not found.")

    response = client.get(f"/v1/files/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_file_detail_handles_a_file_with_no_enrichment_yet(as_member, fake_file_service) -> None:
    file = _FakeFile()
    detail = _FakeFileDetail(
        file=file,
        metadata=None,
        classification=None,
        extraction=None,
        intelligence=None,
        knowledge_attributes=[],
        related_files=[],
    )
    fake_file_service.get_detail.return_value = detail

    response = client.get(f"/v1/files/{file.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"] is None
    assert body["classification"] is None
    assert body["extraction"] is None
    assert body["intelligence"] is None
    assert body["knowledge_attributes"] == []
    assert body["related_files"] == []
