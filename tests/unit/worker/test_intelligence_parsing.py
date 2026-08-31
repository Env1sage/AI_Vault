import json

import pytest
from worker.intelligence.parsing import IntelligenceParseError, parse_response


def test_parses_a_well_formed_response() -> None:
    text = """{
        "document_type": "contract",
        "summary": "A services agreement between two parties.",
        "entities": [{"type": "party", "value": "Acme Corp", "confidence": 0.9}],
        "structured_metadata": {"effective_date": "2026-01-01", "contract_value": "$250,000"},
        "topics": ["services", "payment terms"],
        "confidence": 0.87
    }"""

    result = parse_response(text)

    assert result.document_type == "contract"
    assert result.summary == "A services agreement between two parties."
    assert result.entities == [{"type": "party", "value": "Acme Corp", "confidence": 0.9}]
    assert result.structured_metadata == {
        "effective_date": "2026-01-01",
        "contract_value": "$250,000",
    }
    assert result.topics == ["services", "payment terms"]
    assert result.confidence == 0.87


def test_strips_markdown_json_fences() -> None:
    text = '```json\n{"document_type": "invoice", "summary": null, "entities": [], ' \
        '"structured_metadata": {}, "topics": [], "confidence": 0.5}\n```'

    result = parse_response(text)

    assert result.document_type == "invoice"
    assert result.confidence == 0.5


def test_strips_bare_markdown_fences_without_a_json_tag() -> None:
    text = '```\n{"document_type": "report"}\n```'

    result = parse_response(text)

    assert result.document_type == "report"


def test_non_json_text_raises_parse_error() -> None:
    with pytest.raises(IntelligenceParseError):
        parse_response("I'm sorry, I can't help with that.")


def test_json_array_instead_of_object_raises_parse_error() -> None:
    with pytest.raises(IntelligenceParseError):
        parse_response('["not", "an", "object"]')


def test_truncated_json_raises_parse_error() -> None:
    with pytest.raises(IntelligenceParseError):
        parse_response('{"document_type": "contract", "summary": "Truncat')


def test_missing_keys_degrade_leniently_instead_of_raising() -> None:
    result = parse_response("{}")

    assert result.document_type is None
    assert result.summary is None
    assert result.entities == []
    assert result.structured_metadata == {}
    assert result.topics == []
    assert result.confidence is None


def test_wrong_typed_fields_degrade_leniently() -> None:
    text = '{"document_type": 123, "entities": "not a list", "topics": [1, 2, "three"], ' \
        '"structured_metadata": "not an object"}'

    result = parse_response(text)

    assert result.document_type is None
    assert result.entities == []
    assert result.topics == ["three"]
    assert result.structured_metadata == {}


@pytest.mark.parametrize(
    ("raw_confidence", "expected"),
    [
        (1.5, 1.0),
        (-1, 0.0),
        ("high", None),
        (True, None),
        (None, None),
        (0.42, 0.42),
        (1, 1.0),
    ],
)
def test_confidence_is_clamped_or_none_never_fabricated(
    raw_confidence: object, expected: float | None
) -> None:
    text = json.dumps({"confidence": raw_confidence})

    result = parse_response(text)

    assert result.confidence == expected
