from vault_shared.db.models import File, FileClassification
from worker.intelligence.prompt import _MAX_PROMPT_CHARS, build_messages


def _file(name: str = "Contract.pdf") -> File:
    return File(name=name)


def test_includes_the_file_name_and_extracted_text() -> None:
    messages = build_messages(
        file=_file("ABC_Client_Contract_Final.pdf"),
        classification=None,
        extracted_text="This agreement is made between ABC Ltd and XYZ Corp.",
    )

    user_message = messages[-1]
    assert "ABC_Client_Contract_Final.pdf" in user_message.content
    assert "This agreement is made between ABC Ltd and XYZ Corp." in user_message.content


def test_includes_the_deterministic_classification_hint_when_present() -> None:
    classification = FileClassification(
        document_type="contract", confidence=0.8, method="mime_pdf"
    )

    messages = build_messages(
        file=_file(), classification=classification, extracted_text="Some text."
    )

    assert "contract" in messages[-1].content


def test_uses_unknown_as_the_hint_when_no_classification_exists() -> None:
    messages = build_messages(file=_file(), classification=None, extracted_text="Some text.")

    assert "unknown" in messages[-1].content


def test_truncates_extracted_text_at_the_prompt_char_boundary() -> None:
    long_text = "x" * (_MAX_PROMPT_CHARS + 5_000)

    messages = build_messages(file=_file(), classification=None, extracted_text=long_text)

    # Boundary, not exact length — the user message also contains the file
    # name/hint preamble, so only assert the *text portion* was truncated.
    assert "x" * _MAX_PROMPT_CHARS in messages[-1].content
    assert "x" * (_MAX_PROMPT_CHARS + 1) not in messages[-1].content


def test_system_message_instructs_json_only_output() -> None:
    messages = build_messages(file=_file(), classification=None, extracted_text="text")

    system_message = messages[0]
    assert system_message.role == "system"
    assert "JSON object" in system_message.content
    assert "document_type" in system_message.content
    assert "structured_metadata" in system_message.content
