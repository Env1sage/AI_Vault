import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared import get_logger
from vault_shared.ai_gateway import AIGateway
from vault_shared.db.models import EmbeddingJob, File
from vault_shared.db.repositories import (
    EmbeddingEventRepository,
    EmbeddingJobRepository,
    EmbeddingProgressRepository,
    EmbeddingRepository,
    FileExtractionRepository,
    FileRepository,
    StorageConnectorRepository,
)

logger = get_logger("worker.embedding.embedding_service")


class EmbeddingCancelled(Exception):
    """Mirrors `ScanCancelled`/`EnrichmentCancelled` — unwinds `run()` once
    cooperative cancellation has been observed, without treating
    cancellation as a failure."""


class EmbeddingService:
    """The Embedding Engine (Handbook §8.5) — embeds every file whose
    content extraction succeeded and isn't already embedded at its
    current content hash (Phase 5's `FileExtraction.extracted_text`, not a
    fresh Drive read: this stage's only external dependency is the AI
    Gateway's embedding provider, never Drive itself).

    Unlike the Scanner (ADR-016) and Enrichment (ADR-017) services, this
    one has no `DependencyUnavailableError`/job-level-retry branch — the
    default embedding provider (`LocalEmbeddingProvider`) is fully local
    and offline after its one-time model download, so there is no
    external-connectivity failure mode to retry around. A future cloud
    embedding provider would reintroduce that need; not solved
    speculatively here (ADR-018)."""

    def __init__(self, db: Session, *, ai_gateway: AIGateway) -> None:
        self._db = db
        self._ai_gateway = ai_gateway
        self._connectors = StorageConnectorRepository(db)
        self._files = FileRepository(db)
        self._extractions = FileExtractionRepository(db)
        self._embeddings = EmbeddingRepository(db)
        self._jobs = EmbeddingJobRepository(db)
        self._progress = EmbeddingProgressRepository(db)
        self._events = EmbeddingEventRepository(db)

    def run(self, embedding_job_id: uuid.UUID) -> None:
        job = self._jobs.get_by_id(embedding_job_id)
        if job is None:
            logger.warning(
                "embedding_job_not_found", extra={"embedding_job_id": str(embedding_job_id)}
            )
            return

        connector = self._connectors.get_by_id(job.connector_id)
        if connector is None:
            self._jobs.mark_failed(job, error="Connector no longer exists.")
            self._db.commit()
            return

        self._jobs.mark_running(job)
        # Idempotent: a retried task re-enters `run` for the same
        # embedding_job_id, and `embedding_progress.embedding_job_id` is a
        # primary key, so re-creating it would raise an IntegrityError.
        if self._progress.get_for_job(job.id) is None:
            self._progress.create_for_job(job.id)
        self._events.record(embedding_job_id=job.id, event_type="embedding_started")
        self._db.commit()

        try:
            self._check_cancelled(job.id)
            pending_files = self._files.list_pending_embedding_for_connector(
                job.connector_id,
                model_name=self._ai_gateway.embedding_model_name,
                model_version=self._ai_gateway.embedding_model_version,
            )
            self._progress.set_files_pending(job.id, len(pending_files))
            self._db.commit()

            for file in pending_files:
                self._check_cancelled(job.id)
                self._progress.set_current_file(job.id, file.name)
                self._db.commit()
                self._process_one_file(job, file)
                self._db.commit()
        except EmbeddingCancelled:
            self._jobs.mark_cancelled(job)
            self._events.record(embedding_job_id=job.id, event_type="embedding_cancelled")
            self._db.commit()
            return
        except Exception as exc:  # noqa: BLE001 - job execution boundary must never crash the worker
            logger.exception("embedding_job_failed", extra={"embedding_job_id": str(job.id)})
            self._db.rollback()
            self._jobs.mark_failed(job, error=str(exc))
            self._events.record(
                embedding_job_id=job.id, event_type="embedding_failed", message=str(exc)
            )
            self._db.commit()
            return

        self._jobs.mark_completed(job)
        self._events.record(embedding_job_id=job.id, event_type="embedding_completed")
        self._db.commit()

    def _process_one_file(self, job: EmbeddingJob, file: File) -> None:
        try:
            self._embed_file(file)
            self._progress.increment_processed(job.id)
        except Exception as exc:  # noqa: BLE001 - one file's failure must not stop the job
            logger.exception(
                "file_embedding_failed", extra={"file_id": str(file.id), "job_id": str(job.id)}
            )
            self._db.rollback()
            self._progress.increment_failed(job.id)
            self._events.record(
                embedding_job_id=job.id,
                event_type="file_embedding_failed",
                message=str(exc),
                metadata={"file_id": str(file.id), "file_name": file.name},
            )

    def _embed_file(self, file: File) -> None:
        extraction = self._extractions.get_by_file_id(file.id)
        if extraction is None or not extraction.extracted_text:
            # The "pending" query already filters to successfully-extracted
            # files; this is just defensive against a race with a
            # concurrent re-extraction clearing the text mid-job.
            return

        text = extraction.extracted_text
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        existing = self._embeddings.get_by_file_id(file.id)
        if (
            existing is not None
            and existing.content_hash == content_hash
            and existing.model_name == self._ai_gateway.embedding_model_name
            and existing.model_version == self._ai_gateway.embedding_model_version
        ):
            # Unchanged content *and* the same model/version that produced
            # the stored vector — genuinely nothing to redo. The "pending"
            # query (`list_pending_embedding_for_connector`) already
            # widened its net to include a model/version mismatch even
            # when content hasn't changed; this check has to mirror that
            # exact condition, or a model upgrade would be correctly
            # queued as pending here and then silently skipped anyway.
            return

        [result] = self._ai_gateway.embed([text])
        self._embeddings.upsert(
            file_id=file.id,
            model_name=result.model_name,
            model_version=result.model_version,
            dimensions=result.dimensions,
            vector=result.vector,
            content_hash=content_hash,
            embedded_at=datetime.now(UTC),
        )

    def _check_cancelled(self, embedding_job_id: uuid.UUID) -> None:
        if self._jobs.is_cancel_requested(embedding_job_id):
            raise EmbeddingCancelled()
