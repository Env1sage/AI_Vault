from worker.enrichment.naming import (
    detect_naming_pattern,
    extract_plausible_extension,
    extract_version_number,
    normalize_base_name,
)


def test_detect_naming_pattern_recognizes_explicit_version_tokens() -> None:
    assert detect_naming_pattern("Report_v2.docx") == ("versioned", "v2")
    assert detect_naming_pattern("Report (v10).docx") == ("versioned", "v10")


def test_detect_naming_pattern_recognizes_final_and_draft() -> None:
    assert detect_naming_pattern("Report_Final.docx") == ("final", "final")
    assert detect_naming_pattern("Report_draft.docx") == ("draft", "draft")


def test_detect_naming_pattern_defaults_to_plain() -> None:
    assert detect_naming_pattern("Report.docx") == ("plain", None)


def test_extract_version_number_parses_the_digit() -> None:
    assert extract_version_number("Report_v3.docx") == 3
    assert extract_version_number("Report.docx") is None


def test_normalize_base_name_strips_extension_and_version_tokens() -> None:
    assert normalize_base_name("Report_v1.docx") == "report"
    assert normalize_base_name("Report_v2.docx") == "report"
    assert normalize_base_name("Report_Final.docx") == "report"
    assert normalize_base_name("Quarterly Report.docx") == "quarterly report"


def test_extract_plausible_extension_returns_a_real_extension() -> None:
    assert extract_plausible_extension("Report.docx") == "docx"
    assert extract_plausible_extension("Report.PDF") == "pdf"


def test_extract_plausible_extension_returns_none_without_a_dot() -> None:
    assert extract_plausible_extension("README") is None


def test_extract_plausible_extension_rejects_a_sentence_fragment() -> None:
    """A regression case: some Drive files with no real title fall back to
    a content excerpt as their `name` — a naive "everything after the last
    dot" split would otherwise grab a whole sentence as the "extension",
    overflowing `file_metadata.normalized_extension` (String(50))."""
    name = (
        "Prices may have changed since my last update, so it's advisable "
        "to check with specific meal kit providers for current pricing."
    )
    assert extract_plausible_extension(name) is None


def test_extract_plausible_extension_rejects_anything_with_whitespace() -> None:
    assert extract_plausible_extension("weird name.not an extension") is None
