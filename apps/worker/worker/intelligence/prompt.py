from vault_shared.ai_gateway.interfaces import Message
from vault_shared.db.models import File, FileClassification

# Bounds cost/latency per call — `FileExtraction.extracted_text` is already
# sanitized/truncated upstream by `ContentExtractionService`, but that cap
# (bytes of source file) is much larger than what's sane to hand an LLM in
# one prompt.
_MAX_PROMPT_CHARS = 12_000

_SYSTEM_PROMPT = """You are a document intelligence extractor. Given a file's name, its \
deterministically-detected document type (if known), and its extracted text, return ONLY a \
single JSON object — no markdown fences, no commentary — with exactly these keys:
{
  "document_type": string or null,
  "summary": string (2-4 sentences) or null,
  "entities": [{"type": string, "value": string, "confidence": number 0-1}, ...],
  "structured_metadata": object (fields appropriate to the document type — e.g. a contract \
might include effective_date, expiration_date, contract_value, parties; an invoice might \
include invoice_number, due_date, total; use ISO 8601 for dates),
  "topics": [string, ...],
  "confidence": number 0-1 reflecting your overall certainty in this extraction
}
Never invent a value you cannot support from the text — use null or omit the field instead."""


def build_messages(
    *, file: File, classification: FileClassification | None, extracted_text: str
) -> list[Message]:
    """The deterministic classification (if any) is passed as a hint, not
    a constraint — the LLM can agree with it, refine it, or ignore it; the
    two `document_type` fields (`FileClassification`'s and
    `FileIntelligence`'s) are recorded separately precisely so neither
    silently overwrites the other."""
    hint = classification.document_type if classification is not None else "unknown"
    truncated = extracted_text[:_MAX_PROMPT_CHARS]
    user_content = (
        f"File name: {file.name}\n"
        f"Deterministic document type hint: {hint}\n\n"
        f"Extracted text:\n{truncated}"
    )
    return [
        Message(role="system", content=_SYSTEM_PROMPT),
        Message(role="user", content=user_content),
    ]
