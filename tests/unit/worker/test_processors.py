import uuid
from datetime import UTC, datetime

from vault_shared.db.models import File
from worker.enrichment.extraction import ExtractionOutcome, ExtractionStatus
from worker.enrichment.processors import (
    DEFAULT_PIPELINE,
    EnrichmentContext,
    ExtensionNormalizerProcessor,
    FileTypeClassifierProcessor,
    FolderContextAnalyzerProcessor,
    LanguageDetectionProcessor,
    MimeValidatorProcessor,
    NamingPatternAnalyzerProcessor,
    OwnershipAnalyzerProcessor,
    SharingAnalyzerProcessor,
)


def _make_file(
    *,
    name: str,
    path: str | None = None,
    mime_type: str | None = None,
    owner_email: str | None = None,
    is_shared: bool = False,
    modified: datetime | None = None,
) -> File:
    file = File(storage_source_id=uuid.uuid4(), provider_file_id=str(uuid.uuid4()))
    file.name = name
    file.path = path or f"/{name}"
    file.mime_type = mime_type
    file.owner_email = owner_email
    file.is_shared = is_shared
    file.provider_modified_at = modified
    file.provider_created_at = None
    return file


def _context(file: File, *, extraction: ExtractionOutcome | None = None) -> EnrichmentContext:
    return EnrichmentContext(file=file, extraction=extraction)


def test_extension_normalizer_lowercases_the_extension() -> None:
    result = ExtensionNormalizerProcessor().run(_context(_make_file(name="Report.PDF")))
    assert result.metadata["normalized_extension"] == "pdf"


def test_extension_normalizer_handles_no_extension() -> None:
    result = ExtensionNormalizerProcessor().run(_context(_make_file(name="README")))
    assert result.metadata["normalized_extension"] is None


def test_mime_validator_accepts_a_matching_pair() -> None:
    file = _make_file(name="Report.pdf", mime_type="application/pdf")
    result = MimeValidatorProcessor().run(_context(file))
    assert result.metadata["mime_type_validated"] is True
    assert result.metadata["mime_mismatch_reason"] is None


def test_mime_validator_flags_a_mismatch() -> None:
    file = _make_file(name="Report.pdf", mime_type="image/png")
    result = MimeValidatorProcessor().run(_context(file))
    assert result.metadata["mime_type_validated"] is False
    assert "does not match" in result.metadata["mime_mismatch_reason"]


def test_mime_validator_does_not_flag_an_unknown_extension() -> None:
    file = _make_file(name="Report.xyz", mime_type="application/octet-stream")
    result = MimeValidatorProcessor().run(_context(file))
    assert result.metadata["mime_type_validated"] is True


def test_file_type_classifier_uses_mime_for_images() -> None:
    file = _make_file(name="Photo.jpg", mime_type="image/jpeg")
    result = FileTypeClassifierProcessor().run(_context(file))
    assert result.classification == ("Image", 0.9, "mime_image")


def test_file_type_classifier_uses_extension_for_source_code() -> None:
    file = _make_file(name="main.py", mime_type="text/plain")
    result = FileTypeClassifierProcessor().run(_context(file))
    assert result.classification == ("Source Code", 0.9, "extension_source_code")


def test_file_type_classifier_applies_invoice_keyword_override() -> None:
    file = _make_file(name="Client_Invoice.pdf", mime_type="application/pdf")
    result = FileTypeClassifierProcessor().run(_context(file))
    assert result.classification == ("Invoice", 0.75, "keyword_invoice")


def test_file_type_classifier_does_not_apply_invoice_keyword_to_non_documents() -> None:
    file = _make_file(name="invoice_logo.png", mime_type="image/png")
    result = FileTypeClassifierProcessor().run(_context(file))
    assert result.classification == ("Image", 0.9, "mime_image")


def test_file_type_classifier_falls_back_to_uncategorized() -> None:
    file = _make_file(name="data.bin", mime_type="application/octet-stream")
    result = FileTypeClassifierProcessor().run(_context(file))
    assert result.classification == ("Uncategorized", 0.2, "fallback_uncategorized")


def test_folder_context_analyzer_infers_department_from_path() -> None:
    file = _make_file(name="Budget.xlsx", path="/Finance/Q3/Budget.xlsx")
    result = FolderContextAnalyzerProcessor().run(_context(file))
    assert result.knowledge_attributes == [
        {"attribute_type": "department", "value": "Finance", "confidence": 0.6, "source": "folder_context_analyzer"}
    ]


def test_folder_context_analyzer_has_no_opinion_without_a_keyword_match() -> None:
    file = _make_file(name="Photo.jpg", path="/Misc/Photo.jpg")
    result = FolderContextAnalyzerProcessor().run(_context(file))
    assert result.knowledge_attributes == []


def test_naming_pattern_analyzer_detects_a_version_and_time_period() -> None:
    file = _make_file(name="Report_v2.docx", modified=datetime(2026, 8, 1, tzinfo=UTC))
    result = NamingPatternAnalyzerProcessor().run(_context(file))
    assert result.metadata == {"naming_pattern": "versioned", "version_label": "v2"}
    assert result.knowledge_attributes == [
        {"attribute_type": "time_period", "value": "2026-Q3", "confidence": 1.0, "source": "naming_pattern_analyzer"}
    ]


def test_ownership_analyzer_summarizes_the_owner() -> None:
    file = _make_file(name="Report.docx", owner_email="ada@acme.com")
    result = OwnershipAnalyzerProcessor().run(_context(file))
    assert result.metadata["owner_summary"] == "ada@acme.com"


def test_ownership_analyzer_defaults_to_unknown() -> None:
    file = _make_file(name="Report.docx", owner_email=None)
    result = OwnershipAnalyzerProcessor().run(_context(file))
    assert result.metadata["owner_summary"] == "unknown"


def test_sharing_analyzer_reports_shared_and_private() -> None:
    assert SharingAnalyzerProcessor().run(_context(_make_file(name="a", is_shared=True))).metadata == {
        "sharing_summary": "shared"
    }
    assert SharingAnalyzerProcessor().run(_context(_make_file(name="a", is_shared=False))).metadata == {
        "sharing_summary": "private"
    }


def test_language_detection_returns_no_opinion_without_extracted_text() -> None:
    result = LanguageDetectionProcessor().run(_context(_make_file(name="a"), extraction=None))
    assert result.metadata == {}


def test_language_detection_returns_unknown_for_too_little_text() -> None:
    outcome = ExtractionOutcome(
        status=ExtractionStatus.SUCCESS, extractor_name="plain_text", text="short text", char_count=10, error=None
    )
    result = LanguageDetectionProcessor().run(_context(_make_file(name="a"), extraction=outcome))
    assert result.metadata == {"language": "unknown"}


def test_language_detection_identifies_english_from_stopwords() -> None:
    text = " ".join(["the", "and", "is", "of", "to", "in", "a", "that", "for", "with"] * 3)
    outcome = ExtractionOutcome(
        status=ExtractionStatus.SUCCESS, extractor_name="plain_text", text=text, char_count=len(text), error=None
    )
    result = LanguageDetectionProcessor().run(_context(_make_file(name="a"), extraction=outcome))
    assert result.metadata == {"language": "en"}


def test_default_pipeline_runs_every_registered_processor_without_error() -> None:
    file = _make_file(
        name="Q3_Invoice_Final_v2.pdf",
        path="/Finance/Reports/Q3_Invoice_Final_v2.pdf",
        mime_type="application/pdf",
        owner_email="ada@acme.com",
        is_shared=True,
        modified=datetime(2026, 8, 15, tzinfo=UTC),
    )
    context = _context(file)
    for processor in DEFAULT_PIPELINE:
        processor.run(context)  # must not raise
