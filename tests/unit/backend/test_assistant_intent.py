import pytest
from app.application.assistant.intent import classify_intent

# Every example from the spec's Section 23 — the classifier's real
# acceptance criteria. If one of these stops routing correctly, that's a
# regression a human should see immediately.
_SPEC_EXAMPLES = [
    ("How much storage am I using?", "get_storage_overview"),
    ("What is taking the most space?", "get_storage_statistics"),
    ("Show me duplicate files.", "get_duplicate_summary"),
    ("What are my largest files?", "get_large_files"),
    ("Find files that haven't been used in a year.", "get_inactive_files"),
    ("Which files could I review for cleanup?", "get_cleanup_candidates"),
    ("Show me duplicate PDFs.", "get_duplicate_summary"),
    ("Why are these files considered duplicates?", "get_duplicate_summary"),
    ("Find my largest videos.", "get_large_files"),
    ("How much space could I potentially recover?", "get_storage_overview"),
    ("Show me files related to invoices.", "search_files"),
    ("Find the presentation about the marketing strategy.", "search_files"),
    ("Where is the file called project report.", "search_files"),
    ("What should I clean up first?", "get_cleanup_candidates"),
]


@pytest.mark.parametrize(("question", "expected_tool"), _SPEC_EXAMPLES)
def test_spec_example_questions_route_correctly(question: str, expected_tool: str) -> None:
    calls = classify_intent(question)
    assert len(calls) == 1
    assert calls[0].name == expected_tool


# The chat UI's suggestion chips — kept in sync manually with
# `chat.tsx`'s `SUGGESTIONS` array (Stage 9). Every chip must route
# somewhere real; a chip nobody's classifier recognizes is a broken demo.
_SUGGESTION_CHIPS = [
    ("What is consuming the most storage?", "get_storage_statistics"),
    ("Show me files nobody has opened in a year.", "get_inactive_files"),
    ("Show me duplicates.", "get_duplicate_summary"),
    ("What should I clean up first?", "get_cleanup_candidates"),
]


@pytest.mark.parametrize(("question", "expected_tool"), _SUGGESTION_CHIPS)
def test_suggestion_chips_route_correctly(question: str, expected_tool: str) -> None:
    calls = classify_intent(question)
    assert len(calls) == 1
    assert calls[0].name == expected_tool


def test_uuid_in_question_routes_to_duplicate_group_with_the_id_extracted() -> None:
    group_id = "12345678-1234-5678-1234-567812345678"
    calls = classify_intent(f"Tell me about duplicate group {group_id}")

    assert len(calls) == 1
    assert calls[0].name == "get_duplicate_group"
    assert calls[0].args["group_id"] == group_id


def test_uuid_precedence_beats_the_general_duplicate_summary_rule() -> None:
    """A literal group id must never be swallowed by the broader
    "duplicate" keyword match — the more specific rule wins."""
    group_id = "abcdef12-1234-5678-1234-567812345678"
    calls = classify_intent(f"Why are the files in group {group_id} duplicates?")

    assert calls[0].name == "get_duplicate_group"


@pytest.mark.parametrize(
    ("question", "expected_bytes"),
    [
        ("files over 5 GB", 5 * 1024**3),
        ("anything bigger than 100 mb", 100 * 1024**2),
        ("larger than 2.5 tb", int(2.5 * 1024**4)),
    ],
)
def test_large_files_extracts_the_byte_threshold(question: str, expected_bytes: int) -> None:
    calls = classify_intent(f"Show me the largest files {question}")
    assert calls[0].name == "get_large_files"
    assert calls[0].args["min_size_bytes"] == expected_bytes


def test_large_files_with_no_threshold_omits_the_arg() -> None:
    calls = classify_intent("What are my largest files?")
    assert calls[0].args == {}


@pytest.mark.parametrize(
    ("phrase", "expected_days"),
    [
        ("in 2 years", 730),
        ("in a year", 365),
        ("in 6 months", 180),
        ("in 3 weeks", 21),
        ("in 10 days", 10),
    ],
)
def test_old_files_extracts_the_day_threshold(phrase: str, expected_days: int) -> None:
    calls = classify_intent(f"Show me old files not modified {phrase}")
    assert calls[0].name == "get_old_files"
    assert calls[0].args["older_than_days"] == expected_days


def test_inactive_files_extracts_the_day_threshold() -> None:
    calls = classify_intent("Find files nobody has opened in 2 years")
    assert calls[0].name == "get_inactive_files"
    assert calls[0].args["inactive_days"] == 730


def test_vocabulary_fallback_routes_unmatched_storage_phrasing_to_overview() -> None:
    """An arithmetic question phrased in a way no specific rule catches
    must still land on a tool, not silently fall through to semantic
    search over file content (the worst failure mode for this design)."""
    calls = classify_intent("hows my disk space looking these days")
    assert len(calls) == 1
    assert calls[0].name == "get_storage_overview"


def test_non_storage_question_falls_through_to_rag() -> None:
    calls = classify_intent("What's in the Q3 budget spreadsheet?")
    assert calls == []


def test_empty_question_falls_through_to_rag() -> None:
    assert classify_intent("") == []


def test_compound_question_emits_a_fixed_bundle() -> None:
    calls = classify_intent("How much am I wasting and what should I clean up?")
    assert [c.name for c in calls] == ["get_storage_overview", "get_cleanup_candidates"]


def test_search_files_captures_the_full_question_as_the_query() -> None:
    question = "Find the presentation about the marketing strategy."
    calls = classify_intent(question)
    assert calls[0].args["query"] == question
