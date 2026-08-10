# Phase 6 — Completion Report

**Phase:** [`PHASE_06_FOUNDER_DASHBOARD.md`](PHASE_06_FOUNDER_DASHBOARD.md) — AI Intelligence Engine & Semantic Search Platform (filename is stale — see Technical Debt in the CTO Dashboard; the document's own content is the AI Gateway/embedding/search/RAG layer, not the Founder Dashboard)
**Status:** Implemented by Claude. Awaiting founder manual test and CTO review (Engineering Handbook §4 lifecycle) before being marked complete in [`01_PROJECT_MASTER.md`](../01_PROJECT_MASTER.md).
**Date:** 2026-07-31

---

## 1. Read this first — the architectural decisions this phase required

**ADR-018 — AI Intelligence Engine design.** The phase spec asks for a provider-agnostic embedding/retrieval pipeline behind an AI Gateway, hybrid semantic search, RAG-style context assembly with citations, and conversational querying — with an explicit "no module outside the AI Gateway may communicate directly with an LLM provider" boundary and a cost-minimizing preference for deterministic retrieval over LLM calls. Two decisions were the founder's to make, not Claude's to infer: which LLM provider backs `AIGateway.complete()`, and how embeddings get generated. The founder chose **stub-only completion** (build the full adapter interface; no real LLM key yet — nothing answers with actual LLM reasoning until one is added) and **a local, free, offline embedding model** (no API key, no per-call cost, works offline). Both are binding for this phase. See [ADR-018](../03_ARCHITECTURE_DECISIONS.md#adr-018-ai-intelligence-engine-phase-6--ai-gateway-abstraction-local-first-embeddings-mean-centered-similarity-and-a-stubbed-completion-provider) for the full reasoning, including a real production bug this phase's own testing caught (a job's "460/460 processed" self-reported success masked a re-embedding that never actually happened — see §7 and §8) and the platform-compatibility story behind choosing gensim + GloVe over a transformer.

## 2. Repository changes

```text
packages/shared/vault_shared/
  db/models/
    embedding.py                 NEW — Embedding (1:1 w/ File: model_name, model_version, dimensions,
                                 vector ARRAY(Float), content_hash, embedded_at)
    embedding_job.py             NEW — EmbeddingJob (+ EmbeddingJobStatus, EmbeddingTrigger), mirrors EnrichmentJob
    embedding_progress.py        NEW — EmbeddingProgress, mirrors EnrichmentProgress
    embedding_event.py           NEW — EmbeddingEvent, mirrors EnrichmentEvent (append-only)
    conversation.py              NEW — Conversation (org + user scoped, title, messages relationship)
    conversation_message.py      NEW — ConversationMessage (+ MessageRole), role/content/retrieval_method/
                                 provider/token_usage, citations relationship
    citation.py                  NEW — Citation (message_id, file_id, snippet, confidence, retrieval_method)
    search_session.py            NEW — SearchSession (append-only query log: query_text, result_count)
  db/repositories/
    embedding_repository.py, embedding_job_repository.py, embedding_progress_repository.py,
    embedding_event_repository.py, conversation_repository.py, conversation_message_repository.py,
    citation_repository.py, search_session_repository.py                NEW — one per model above
    file_repository.py           + list_pending_embedding_for_connector (model-name/version-aware),
                                 search_for_organization (name/metadata/knowledge-attribute ILIKE match)
  ai_gateway/                    NEW — the AI Gateway itself
    interfaces.py                EmbeddingResult, EmbeddingProvider (Protocol), Message, CompletionResult,
                                 CompletionProvider (Protocol)
    gateway.py                   AIGateway: embed(), complete(), embedding_model_name/version properties
    similarity.py                rank_by_similarity — mean-centered cosine similarity (the SIF-style fix)
    providers/local_embedding_provider.py   LocalEmbeddingProvider — gensim + glove-wiki-gigaword-100,
                                 stopword-filtered averaging, unit-normalized (_MODEL_VERSION="2")
    providers/extractive_completion_provider.py   ExtractiveCompletionProvider — deterministic fallback,
                                 never invents an answer
    __init__.py                  get_ai_gateway() — lru_cached factory, the only provider-selection point

apps/worker/worker/embedding/
  embedding_service.py           NEW — EmbeddingService: run/_process_one_file/_embed_file/_check_cancelled;
                                 EmbeddingCancelled exception; no job-level retry (no external-connectivity
                                 failure mode for the local provider) — see ADR-018

apps/worker/worker/tasks/
  embedding.py                   NEW — worker.embedding.run Celery task, no retry policy
  enrichment.py                  + _enqueue_embedding_if_enrichment_completed (auto-chains after enrichment)
  celery_app.py                  + "worker.tasks.embedding" in the include list

apps/backend/app/
  application/
    search_service.py             NEW — SearchService: hybrid metadata+semantic search, dataclass SearchResult
    context_builder_service.py    NEW — ContextBuilderService: rank/dedupe/token-budget context assembly,
                                  CitationCandidate/ContextBundle dataclasses
    conversation_service.py       NEW — ConversationService: ask() orchestrates retrieval → context →
                                  AIGateway.complete() → citation persistence; get_detail(), AssistantTurn/
                                  ConversationDetail dataclasses
    embedding_job_service.py      NEW — EmbeddingJobService: list_for_connector, get_owned, get_progress,
                                  start, cancel — mirrors EnrichmentJobService exactly
  infrastructure/queue/
    embedding_producer.py         NEW — enqueue_embedding_job, same task-name-string pattern as scans/enrichment
  presentation/
    api/v1/search.py               NEW — POST /search
    api/v1/conversations.py        NEW — GET/POST /conversations, GET /conversations/{id},
                                  POST /conversations/{id}/messages
    api/v1/embedding.py            NEW — POST/GET /connectors/{id}/embedding, GET/POST /embedding/{id}(/cancel)
    api/v1/schemas.py              + EmbeddingProgressResponse, EmbeddingJobResponse, SearchRequest,
                                  SearchResultResponse, SearchResponse, CitationResponse,
                                  ConversationMessageResponse, ConversationResponse,
                                  ConversationDetailResponse, AskRequest, AskResponse
    api/v1/router.py               + embedding_router, search_router, conversations_router
    dependencies/services.py       + get_embedding_job_service, get_search_service,
                                  get_context_builder_service, get_conversation_service
  alembic/versions/0006_ai_intelligence_tables.py   embeddings, embedding_jobs, embedding_events,
                                  embedding_progress, conversations, conversation_messages, citations,
                                  search_sessions (full downgrade() included)

packages/shared/pyproject.toml   + gensim>=4.3,<5
packages/config/python/mypy.ini  python_version 3.11 → 3.12 (numpy's own stubs need 3.12+ syntax;
                                 does not change either app's actual runtime, both run 3.13)

packages/types/src/search.ts, conversations.ts, embedding.ts   NEW — RetrievalMethod, SearchRequest/Response/
                                  Result, AskRequest/Response, Citation, Conversation(Detail), ConversationMessage,
                                  EmbeddingJob(Status/Trigger), EmbeddingProgress
packages/types/src/index.ts       + re-exports

apps/frontend/src/
  routes/search.tsx               NEW — query box, ranked results with retrieval-method badge + score,
                                  linking into /files/$fileId
  routes/chat.tsx                 NEW — conversation list, new-conversation question box
  routes/chat.$conversationId.tsx NEW — message thread, per-message citation panel, follow-up question box
  routes/scans.tsx                + "Embedding" section (status/progress, start/cancel), mirrors Enrichment
  routes/dashboard.tsx             + "Search"/"Chat" nav links
  lib/embedding-status.ts (+ conventions matching enrichment-status.ts)   embeddingStatusColor,
                                  isActiveEmbeddingStatus — pure, unit-tested pattern
  lib/retrieval-method.ts          retrievalMethodLabel, retrievalMethodColor — pure helper for search/chat badges

tests/unit/backend/test_embedding_router.py, test_search_router.py,
  test_conversations_router.py                                          NEW — 15 + 4 + 9 tests
tests/integration/backend/test_embedding_job_service_integration.py,
  test_search_service_integration.py, test_conversation_service_integration.py   NEW — 6 + 4 + 4 tests,
  real Postgres/Redis
tests/unit/shared/test_similarity.py, test_local_embedding_provider.py,
  test_extractive_completion_provider.py                                NEW — 4 + 5 + 3 tests
tests/integration/worker/test_embedding_service_integration.py           NEW — 5 tests, real Postgres
```

## 3. Database changes

Migration `0006_ai_intelligence_tables` (on top of Phase 5's `0005_knowledge_engine_tables`):

- **`embeddings`** — 1:1 with `files` (shared PK `file_id`). `model_name`/`model_version` let a re-embedding need (model change) be detected without silently comparing vectors from different models; `vector` is a plain Postgres `ARRAY(Float)` (brute-force similarity in application code, no pgvector — Handbook §9/§22's deferred vector store); `content_hash` (sha256 of the embedded text) lets `EmbeddingService` skip a file whose content hasn't actually changed even if it was re-extracted.
- **`embedding_jobs`** / **`embedding_progress`** / **`embedding_events`** — mirror `enrichment_jobs`/`enrichment_progress`/`enrichment_events` exactly (same status lifecycle, same cooperative-cancellation column, same live-counters-in-a-separate-table reasoning). `embedding_jobs.enrichment_job_id` (nullable, `ON DELETE SET NULL`) links a job back to the enrichment run that triggered it, when applicable.
- **`conversations`** — org- and user-scoped (Handbook §13's tenant boundary, plus a stricter per-user boundary the phase spec explicitly asks for: "user-specific conversation history"). `title` is derived from the first question asked, truncated to 80 characters.
- **`conversation_messages`** — one row per turn (`role` = user/assistant). Only assistant messages carry `retrieval_method`/`provider`/`token_usage` — `provider` records which AI Gateway adapter actually answered, proving provider-interchangeability per-message rather than assuming it from config.
- **`citations`** — a structured source reference per assistant message, not a JSON blob — `file_id`, a truncated `snippet`, `confidence`, and `retrieval_method` (how this file was found: metadata, semantic, or both). No in-document location (page/line) this phase — see §8.
- **`search_sessions`** — an append-only logged query (`query_text`, `result_count`) for history/observability, not the result set itself (ephemeral, returned directly to the caller).

Verified via `alembic upgrade head --sql` (correct SQL) and applied for real against the founder's live local Postgres instance (`alembic upgrade head` succeeded, `0005 → 0006`).

## 4. API surface

```text
POST   /v1/search                            (any authenticated org member)  → { query, results: SearchResult[] }
GET    /v1/conversations                      (any authenticated org member)  → Conversation[] (own only)
POST   /v1/conversations                      (any authenticated org member)  → AskResponse (201, new conversation)
GET    /v1/conversations/{id}                 (any authenticated org member)  → ConversationDetail (own only)
POST   /v1/conversations/{id}/messages        (any authenticated org member)  → AskResponse (201, follow-up)
POST   /v1/connectors/{id}/embedding          (owner/admin)                    → EmbeddingJob (201)
GET    /v1/connectors/{id}/embedding          (any authenticated org member)  → EmbeddingJob[]
GET    /v1/embedding/{id}                     (any authenticated org member)  → EmbeddingJob (with progress)
POST   /v1/embedding/{id}/cancel              (owner/admin)                    → EmbeddingJob
```

Conversations are checked against both `organization_id` *and* `user_id` (`ConversationRepository.get_owned`) — stricter than every prior phase's org-only ownership check, since chat history is explicitly per-user. RBAC for embedding jobs mirrors Phase 5's enrichment API exactly (owner/admin to start/cancel, any org member to read).

## 5. Worker behavior

`EmbeddingService.run(embedding_job_id)`: loads the job and connector, marks `RUNNING`, queries `FileRepository.list_pending_embedding_for_connector` — every `File` with successfully extracted text and (no `Embedding` row yet, or a newer extraction, or a stored `model_name`/`model_version` that no longer matches the currently-configured provider) — and for each: computes a content hash of the extracted text, skips if an existing embedding already has both that same hash *and* the current model's identity (this second condition was a real bug fixed mid-phase — see §7/§8), otherwise calls `AIGateway.embed([text])` and upserts the resulting vector. No job-level retry exists (unlike Scanner/Enrichment) — the local embedding provider has no external-connectivity failure mode to retry around, a deliberate ADR-018 scope decision, not an oversight. Per-file failures are caught, logged, and recorded as a normal `files_failed` increment plus an `EmbeddingEvent`, never stopping the rest of the job. Cancellation is checked once per file via the same column-only-query pattern as the scanner/enrichment services.

`worker/tasks/enrichment.py`'s `_enqueue_embedding_if_enrichment_completed` runs after every successful enrichment: it creates an `EmbeddingJob` (`triggered_by=ENRICHMENT_COMPLETED`, linked via `enrichment_job_id`) and calls `run_embedding.delay(...)` directly — same plain in-process Celery call pattern as the scan→enrichment chain. Skipped if an embedding job is already active for that connector, or if enrichment didn't complete successfully.

## 6. Performance considerations

- **Query-time mean-centering, not stored per-vector.** `rank_by_similarity` computes its correction fresh from whichever query and candidate pool are being compared right now — the "generic direction" to remove is a property of the current comparison, not any single stored embedding, so nothing about a stored vector needs to change when the candidate pool changes.
- **Brute-force similarity is bounded by organization size, not global scale.** `EmbeddingRepository.list_for_organization` scopes to one org's files only — consistent with Handbook §9/§22's explicit deferral of a dedicated vector store to a much larger scale than this project currently operates at.
- **Context assembly respects a character budget.** `ContextBuilderService` stops adding ranked results once ~8,000 characters (a rough `4 chars ≈ 1 token` stand-in) are assembled, so a single conversational turn's context can't grow unbounded regardless of how many files a query matches; `ConversationService` additionally caps the search pool feeding a chat answer to 6 results (tighter than the standalone `/search` page's 20) so a citation panel stays readable.
- **Word-count cap on embedding input.** `LocalEmbeddingProvider` averages at most the first 5,000 words of a document — a document's topic is adequately captured well before that, and it keeps per-file embedding time roughly constant regardless of how long `FileExtraction.extracted_text` is (itself already capped at 200,000 characters since Phase 5).

## 7. Tests and what was actually verified in this environment

- **Backend:** 181 tests total (37 new — 23 router unit tests for `/v1/embedding`, `/v1/search`, `/v1/conversations` via `TestClient` + `dependency_overrides`, same pattern as every prior router; 14 new integration tests against real Postgres/Redis: `EmbeddingJobService` start/list/get/cancel + active-job conflict + cross-org rejection, mirroring `EnrichmentJobService`'s suite exactly; `SearchService` — name-substring match, semantic ranking via a fixed-vector test double, "both"-method merging, org isolation; `ConversationService` — new-conversation creation with derived title, no-context fallback message, follow-up continuity within one conversation, cross-user rejection). `ruff`/`mypy` clean.
- **Worker:** 91 tests total (5 new integration tests against real Postgres: pending-files processing and persistence, resumable skip-if-unchanged, **a model-version-change re-embedding test that caught a real bug** — see §8 — per-file failure isolation, cancellation; 12 new unit tests: `rank_by_similarity`'s empty/aligned/orthogonal/opposite/degenerate-single-candidate cases, `LocalEmbeddingProvider._embed_one`'s averaging/stopword-filtering/unknown-word/case-insensitivity behavior against a fake `KeyedVectors` stand-in — no real gensim download in any test, `ExtractiveCompletionProvider`'s no-context/with-context/length-bound behavior). `ruff`/`mypy` clean.
- **Frontend:** `tsc --noEmit`, `eslint .` clean on the new `/search`, `/chat`, `/chat/$conversationId` routes and the `scans.tsx` Embedding section; TanStack Router's dev-server codegen confirmed all three new routes register correctly in the generated route tree. One pre-existing, unrelated vitest failure (`google-sign-in-button.test.tsx`, an `act()`-wrapping issue in a Phase 2 component this phase never touched) — not a regression from this phase's work.
- **Live, not just mocked — and this caught a real bug.** Unlike every prior phase, this phase's core pipeline was exercised end-to-end against a real local Postgres/Redis instance and the founder's actual connected Google Drive account: a full scan→enrich→embed run over ~470 real files, `POST /v1/search` and the full `/v1/conversations` flow hit via real HTTP with a minted JWT against a running `uvicorn` server, and — critically — a direct query of the real `embeddings` table's `model_version` distribution after a job reported "460/460 processed, 0 failed" revealed every row still said `model_version="1"`, proving the job's own progress counters didn't mean what they appeared to mean. Root cause: `EmbeddingService._embed_file`'s skip-if-unchanged check compared only content hash, not model identity, so a file correctly queued as "pending" by the model-version-aware query was then silently skipped anyway. Fixed (`_embed_file` now requires both to match before skipping), covered by a new regression test that asserts the embedding provider is actually re-invoked on a model-version bump (not just that the job reports success), and re-verified against the same real data: a second real re-embedding run moved all 443 real files to `model_version="2"`, and `rank_by_similarity` against those genuinely-new vectors reproduced the expected good discrimination (portal/admin documents scoring 0.66–0.86 against each other, completely unrelated documents scoring −0.42 to −0.53) — this is the actual, correct validation of the stopword-filtering fix; an earlier same-session check that appeared to confirm this was, in retrospect, unknowingly reading stale v1 vectors.
- **Test-data note:** this phase's real-Postgres integration tests run against the same database as the founder's real application data (no isolated test DB is configured — the same `requires_infra` convention Phases 1-5 already established), so they leave a handful of extra organizations/connectors/files in the local dev database. Not a regression or new behavior — flagged here because it's directly what explained the initial 470-vs-473-embeddings discrepancy noticed while investigating the bug above.

**Concrete manual-test steps for the founder**, beyond Phase 1-5's checklist: with a connected Workspace connector and at least one completed enrichment, confirm an embedding job auto-starts (visible on `/scans`'s new Embedding section) without any manual action; once it completes, visit `/search`, run a query that should hit a real file by name and confirm it shows a "Name match" badge; run a query about a topic (not a filename) and confirm semantically related files surface with a "Semantic match" badge and a plausible score; visit `/chat`, ask a question, and confirm the response is clearly labeled as not using a real AI model yet (`ExtractiveCompletionProvider`'s explicit disclaimer text) while still surfacing genuinely relevant file excerpts and a citation panel linking back to real files; ask a follow-up in the same conversation and confirm it's appended to the same thread.

## 8. Known limitations / follow-ups

- Same `packages/types` manual-sync caveat as prior phases (ADR-012), now also covering `search.ts`/`conversations.ts`/`embedding.ts`.
- **`LocalEmbeddingProvider`'s bag-of-word-vectors technique is a real but materially weaker semantic signal than a modern sentence-transformer** — an explicit, documented platform-compatibility and zero-cost tradeoff (no `torch`/`onnxruntime` wheels available on this development platform), not a target quality bar. Revisit if a wheel-compatible transformer or an acceptable paid embedding API becomes available.
- **No real LLM reasoning in this phase** — `ExtractiveCompletionProvider` never invents an answer but also never actually reasons; every "chat" response is deterministic retrieval dressed as a reply, per the founder's explicit "stub only" choice. The full adapter abstraction is built and ready for a real provider with a two-line factory change.
- **`SearchService` doesn't filter by current embedding model version** — a file whose stored vector predates a model/version change still participates in semantic ranking alongside current-model vectors until it's re-processed by a fresh embedding job. Not a correctness bug (a full re-embedding run correctly migrates every file), but worth a filter or a "N files pending re-embedding" surfacing before this silently degrades ranking quality at real scale.
- **Citations are file-level only** — no page/line/paragraph anchor within a file. Deferred scope per ADR-018, revisit once a real LLM provider makes finer-grained citation meaningfully actionable.
- **A job's self-reported progress counters are not proof its per-item logic actually did the work** — the real bug described in §7 above. Fixed for this phase's specific case; worth keeping in mind generally for any future job-style service in this codebase (verify against the data a job changed, not just its completion status).
- Route components remain outside the automated test suite by consistent design choice (see §7) — standing item in the CTO Dashboard's Technical Debt.
- Phase roadmap numbering/filename mismatch (this phase's content lives inside `PHASE_06_FOUNDER_DASHBOARD.md`, whose actual next-phase content per its own in-document roadmap revision is the Founder Command Center) — left unresolved at the founder's standing instruction, noted in the CTO Dashboard.

## 9. Recommendation for Phase 7

Every embedded file now carries a version-tracked vector, and `SearchService`/`ContextBuilderService`/`ConversationService` give a working, fully-attributed retrieval pipeline with citations — exactly the surface a Founder Command Center / Recommendation Engine (per `PHASE_07_EXECUTION_ENGINE.md`'s own in-document roadmap revision, this is Phase 7's actual content) should build on: `ContextBuilderService` was deliberately kept independent of the conversational flow specifically so a recommendation engine can call it directly for its own context needs, and `SearchResult`/`CitationCandidate` are already the kind of explainable, confidence-scored, method-labeled output a recommendation UI needs to justify itself to a founder. Two concrete follow-ups worth prioritizing early in Phase 7: (1) decide whether recommendations require real LLM reasoning (if so, wiring an actual `CompletionProvider` becomes a Phase 7 blocker, not a nice-to-have) and (2) the model-version search-time filtering gap noted in §8, since a recommendation engine reasoning over "all embedded files" is exactly the kind of consumer that would be silently affected by stale, mixed-model-version vectors.
