import hashlib
import tempfile
import uuid
import zipfile
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared import ConflictError, NotFoundError, ValidationError, get_logger, get_settings
from vault_shared.connector_service import ConnectorTokenService
from vault_shared.connectors.google_drive import DriveFile, GoogleDriveClient
from vault_shared.connectors.google_workspace import GoogleWorkspaceOAuthClient
from vault_shared.db.models import (
    ArchiveJobStatus,
    ExecutionActionType,
    ExecutionJob,
    ExecutionPlan,
    ExecutionPlanStatus,
    ExecutionResultStatus,
    ExecutionStep,
    ExecutionStepStatus,
    File,
    RecommendationTrigger,
    RollbackRecord,
    StorageAnalysisTrigger,
    VerificationStatus,
)
from vault_shared.db.repositories import (
    ArchiveJobRepository,
    ConnectorCredentialsRepository,
    ExecutionAuditRepository,
    ExecutionJobRepository,
    ExecutionPlanRepository,
    ExecutionResultRepository,
    ExecutionStepRepository,
    FileRepository,
    RecommendationJobRepository,
    RollbackRecordRepository,
    StorageAnalysisJobRepository,
    StorageConnectorRepository,
)
from vault_shared.execution import validate_execution_permissions
from vault_shared.object_storage import ObjectStorageClient
from worker.tasks.recommendation import run_recommendation
from worker.tasks.storage_intelligence import run_storage_intelligence

logger = get_logger("worker.execution.execution_service")

_TRASHABLE_ACTIONS = (ExecutionActionType.ARCHIVE, ExecutionActionType.REMOVE_DUPLICATE)
_MOVE_ACTIONS = (ExecutionActionType.MOVE_FILE, ExecutionActionType.MOVE_FOLDER)

# Archive MVP export choices — deliberately different from extraction.py's
# _GOOGLE_NATIVE_EXPORTS (which targets text/csv for search-indexing). An
# archive is meant to be a usable backup, not extracted text, so Docs/Slides
# export to PDF and Sheets to xlsx.
_ARCHIVE_EXPORT_MIME_TYPES: dict[str, str] = {
    "application/vnd.google-apps.document": "application/pdf",
    "application/vnd.google-apps.presentation": "application/pdf",
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
}


class ExecutionCancelled(Exception):
    """Unwinds `run()` once cooperative cancellation has been observed —
    mirrors `ScanCancelled`/`EnrichmentCancelled`/`EmbeddingCancelled`."""


class ExecutionPaused(Exception):
    """Unwinds `run()` once cooperative pause has been observed. Unlike
    cancellation, the job is left in a resumable state — `run()`'s
    top-level handler for this is a no-op, since the pausing branch
    already committed the `PAUSED` status before raising."""


class ExecutionService:
    """The Execution Engine (Handbook §8.7) — the *only* module in this
    codebase permitted to perform a mutating call against connected
    storage, and the only one to ever touch `GoogleDriveClient`'s write
    methods. `run()` branches on `ExecutionJob.is_rollback` to either
    carry out an approved plan's steps forward or reverse a plan's
    already-executed steps via their `RollbackRecord`s — both paths share
    one job lifecycle, cooperative cancel/pause, per-step failure
    isolation, and audit trail. See ADR-020."""

    def __init__(
        self,
        db: Session,
        *,
        drive_client: GoogleDriveClient,
        oauth_client: GoogleWorkspaceOAuthClient,
        object_storage_client: ObjectStorageClient,
    ) -> None:
        self._db = db
        self._drive = drive_client
        self._object_storage = object_storage_client
        self._tokens = ConnectorTokenService(db, oauth_client=oauth_client)
        self._connectors = StorageConnectorRepository(db)
        self._credentials = ConnectorCredentialsRepository(db)
        self._plans = ExecutionPlanRepository(db)
        self._steps = ExecutionStepRepository(db)
        self._jobs = ExecutionJobRepository(db)
        self._results = ExecutionResultRepository(db)
        self._rollback_records = RollbackRecordRepository(db)
        self._files = FileRepository(db)
        self._audits = ExecutionAuditRepository(db)
        self._archive_jobs = ArchiveJobRepository(db)
        self._storage_analysis_jobs = StorageAnalysisJobRepository(db)
        self._recommendation_jobs = RecommendationJobRepository(db)

    def run(self, execution_job_id: uuid.UUID) -> None:
        job = self._jobs.get_by_id(execution_job_id)
        if job is None:
            logger.warning(
                "execution_job_not_found", extra={"execution_job_id": str(execution_job_id)}
            )
            return

        plan = self._plans.get_by_id(job.execution_plan_id)
        if plan is None:
            self._jobs.mark_failed(job, error="Execution plan no longer exists.")
            self._db.commit()
            return

        connector = self._connectors.get_by_organization_and_provider(
            organization_id=plan.organization_id, provider=plan.target_provider
        )
        credentials = (
            self._credentials.get_by_connector_id(connector.id) if connector else None
        )
        failures = validate_execution_permissions(connector=connector, credentials=credentials)
        if failures:
            error = "; ".join(failures)
            self._jobs.mark_failed(job, error=error)
            self._audits.record(
                organization_id=plan.organization_id,
                execution_plan_id=plan.id,
                execution_job_id=job.id,
                event_type="execution_failed",
                message=error,
            )
            self._db.commit()
            return

        self._jobs.mark_running(job)
        self._audits.record(
            organization_id=plan.organization_id,
            execution_plan_id=plan.id,
            execution_job_id=job.id,
            event_type="execution_started",
            metadata={"is_rollback": job.is_rollback},
        )
        if not job.is_rollback:
            self._plans.update_status(plan, status=ExecutionPlanStatus.EXECUTING)
        self._db.commit()

        assert connector is not None  # validate_execution_permissions already checked this
        access_token = self._tokens.get_valid_access_token(connector)

        try:
            if job.is_rollback:
                self._run_rollback(job, plan, access_token=access_token)
            else:
                self._run_forward(job, plan, access_token=access_token)
        except ExecutionCancelled:
            self._jobs.mark_cancelled(job)
            self._audits.record(
                organization_id=plan.organization_id,
                execution_plan_id=plan.id,
                execution_job_id=job.id,
                event_type="execution_cancelled",
            )
            self._db.commit()
        except ExecutionPaused:
            pass  # the pausing branch already committed PAUSED before raising
        except Exception as exc:  # noqa: BLE001 - job execution boundary must never crash the worker
            logger.exception("execution_job_failed", extra={"execution_job_id": str(job.id)})
            self._db.rollback()
            self._jobs.mark_failed(job, error=str(exc))
            self._audits.record(
                organization_id=plan.organization_id,
                execution_plan_id=plan.id,
                execution_job_id=job.id,
                event_type="execution_failed",
                message=str(exc),
            )
            self._db.commit()

    # ------------------------------------------------------------------
    # Forward execution
    # ------------------------------------------------------------------

    def _run_forward(self, job: ExecutionJob, plan: ExecutionPlan, *, access_token: str) -> None:
        steps = self._steps.list_for_plan(plan.id)

        # CREATE_ARCHIVE is the one action type that isn't "one step = one
        # independent mutation" — N files become ONE zip in ONE object
        # storage write, so all of a plan's CREATE_ARCHIVE steps are
        # completed together here, before the per-step loop below (which
        # only ever processes still-PENDING steps) ever reaches them.
        # Cancellation is checked once, before the batch starts, not
        # per-file within it — zip-building isn't resumable mid-stream.
        pending_archive_steps = [
            step
            for step in steps
            if step.action_type == ExecutionActionType.CREATE_ARCHIVE
            and step.status == ExecutionStepStatus.PENDING
        ]
        if pending_archive_steps:
            self._check_cancelled(job.id)
            self._execute_archive_batch(
                job, plan, pending_archive_steps, access_token=access_token
            )

        succeeded = 0
        failed = 0
        for step in steps:
            if step.status != ExecutionStepStatus.PENDING:
                # Resuming a previously-paused job — already-decided steps
                # are never re-executed.
                if step.status == ExecutionStepStatus.COMPLETED:
                    succeeded += 1
                elif step.status == ExecutionStepStatus.FAILED:
                    failed += 1
                continue

            self._check_cancelled(job.id)
            if self._jobs.is_pause_requested(job.id):
                self._jobs.mark_paused(job)
                self._audits.record(
                    organization_id=plan.organization_id,
                    execution_plan_id=plan.id,
                    execution_job_id=job.id,
                    event_type="execution_paused",
                )
                self._db.commit()
                raise ExecutionPaused

            if self._execute_forward_step(job, plan, step, access_token=access_token):
                succeeded += 1
            else:
                failed += 1

        if failed == 0:
            self._jobs.mark_completed(job)
            self._plans.update_status(plan, status=ExecutionPlanStatus.COMPLETED)
        elif succeeded == 0:
            self._jobs.mark_failed(job, error="All steps failed.")
            self._plans.update_status(plan, status=ExecutionPlanStatus.FAILED)
        else:
            self._jobs.mark_partially_completed(job)
            self._plans.update_status(plan, status=ExecutionPlanStatus.PARTIALLY_COMPLETED)

        self._audits.record(
            organization_id=plan.organization_id,
            execution_plan_id=plan.id,
            execution_job_id=job.id,
            event_type="execution_completed",
            metadata={"succeeded": succeeded, "failed": failed},
        )
        self._db.commit()

        if any(
            step.action_type in _TRASHABLE_ACTIONS and step.status == ExecutionStepStatus.COMPLETED
            for step in steps
        ):
            self._trigger_storage_refresh(plan.organization_id)

    def _execute_forward_step(
        self, job: ExecutionJob, plan: ExecutionPlan, step: ExecutionStep, *, access_token: str
    ) -> bool:
        now = datetime.now(UTC)
        try:
            file = self._files.get_by_id(step.target_file_id)
            if file is None:
                raise NotFoundError("Target file no longer exists in this platform's inventory.")

            # Live "resource existence" + "current file state" validation
            # (Phase 8 spec) — right before mutating, since Drive state can
            # have drifted since the plan was created or even since
            # approval.
            current = self._drive.get_file(
                access_token=access_token, file_id=file.provider_file_id
            )
            if current.trashed:
                raise ConflictError(
                    "File is already trashed outside this platform — nothing to do."
                )

            # The authoritative rollback source — captured and committed
            # *before* the live mutation, so a failure after a successful
            # Drive write can never leave a mutation with no way back.
            pre_state = self._pre_mutation_state(step.action_type, current)
            self._rollback_records.create(execution_step_id=step.id, pre_state=pre_state)
            self._db.commit()

            self._apply_action(step, access_token=access_token, file=file, current=current)
        except Exception as exc:  # noqa: BLE001 - one file's failure must not stop the job
            logger.exception("execution_step_failed", extra={"execution_step_id": str(step.id)})
            self._db.rollback()
            self._steps.mark_failed(step)
            self._results.create(
                execution_job_id=job.id,
                execution_step_id=step.id,
                status=ExecutionResultStatus.FAILED,
                verification_status=VerificationStatus.SKIPPED,
                error=str(exc),
                executed_at=now,
                verified_at=None,
            )
            self._audits.record(
                organization_id=plan.organization_id,
                execution_plan_id=plan.id,
                execution_job_id=job.id,
                event_type="step_failed",
                message=str(exc),
                metadata={"execution_step_id": str(step.id), "action_type": step.action_type},
            )
            self._db.commit()
            return False

        # The mutation itself succeeded — a verification problem is
        # recorded, not treated as step failure (Phase 8 spec: "Verification
        # failures should trigger recovery procedures," not undo a
        # successful action retroactively).
        try:
            verified = self._verify_forward(step, access_token=access_token, file=file)
            verification_status = (
                VerificationStatus.VERIFIED if verified else VerificationStatus.FAILED
            )
        except Exception:  # noqa: BLE001 - verification itself failing is not a step failure
            logger.exception(
                "execution_step_verification_failed", extra={"execution_step_id": str(step.id)}
            )
            verification_status = VerificationStatus.FAILED

        self._steps.mark_completed(step)
        self._results.create(
            execution_job_id=job.id,
            execution_step_id=step.id,
            status=ExecutionResultStatus.SUCCESS,
            verification_status=verification_status,
            error=None,
            executed_at=now,
            verified_at=datetime.now(UTC),
        )
        self._audits.record(
            organization_id=plan.organization_id,
            execution_plan_id=plan.id,
            execution_job_id=job.id,
            event_type="step_completed",
            metadata={
                "execution_step_id": str(step.id),
                "action_type": step.action_type,
                "verification_status": verification_status,
            },
        )
        self._db.commit()
        return True

    @staticmethod
    def _pre_mutation_state(action_type: str, current: DriveFile) -> dict:
        if action_type in _TRASHABLE_ACTIONS:
            return {"trashed": False}
        if action_type == ExecutionActionType.RENAME:
            return {"name": current.name}
        if action_type in _MOVE_ACTIONS:
            return {"parent_folder_id": current.parents[0] if current.parents else None}
        return {}

    def _apply_action(
        self, step: ExecutionStep, *, access_token: str, file: File, current: DriveFile
    ) -> None:
        action_type = step.action_type
        if action_type in _TRASHABLE_ACTIONS:
            self._drive.set_trashed(
                access_token=access_token, file_id=file.provider_file_id, trashed=True
            )
            # The local mirror's only record that this file left active
            # storage — excluded from every Storage Intelligence/Dashboard
            # total from here on (FileRepository._for_organization etc.),
            # without deleting the row (see File.trashed's docstring on why).
            self._files.mark_trashed(file, trashed=True)
        elif action_type == ExecutionActionType.RENAME:
            new_name = step.planned_change.get("new_name")
            if not new_name:
                raise ValidationError("Rename step has no target name.")
            self._drive.rename_file(
                access_token=access_token, file_id=file.provider_file_id, new_name=new_name
            )
        elif action_type in _MOVE_ACTIONS:
            new_parent_id = step.planned_change.get("new_parent_id")
            old_parent_id = current.parents[0] if current.parents else None
            if not new_parent_id or not old_parent_id:
                raise ValidationError("Move step is missing a source or target parent folder.")
            self._drive.move_file(
                access_token=access_token,
                file_id=file.provider_file_id,
                add_parent_id=new_parent_id,
                remove_parent_id=old_parent_id,
            )
        elif action_type == ExecutionActionType.UPDATE_METADATA:
            properties = step.planned_change.get("properties")
            if not properties:
                raise ValidationError("Update-metadata step has no properties to set.")
            self._drive.update_app_properties(
                access_token=access_token, file_id=file.provider_file_id, properties=properties
            )
        else:
            raise ValidationError(f"Unsupported action type: {action_type}")

    # ------------------------------------------------------------------
    # Archive MVP — one batch operation completing N CREATE_ARCHIVE steps
    # ------------------------------------------------------------------

    def _fetch_file_bytes(self, file: File, *, access_token: str) -> bytes | None:
        """Returns `None` for a file this archive can't meaningfully
        contain — a Google-native type with no exportable binary (Forms,
        Sites, Drawings) or a folder. Callers treat that as an individual
        step failure, not a batch failure."""
        mime = file.mime_type or ""
        if mime in _ARCHIVE_EXPORT_MIME_TYPES:
            return self._drive.export_file(
                access_token=access_token,
                file_id=file.provider_file_id,
                export_mime_type=_ARCHIVE_EXPORT_MIME_TYPES[mime],
            )
        if mime.startswith("application/vnd.google-apps."):
            return None
        return self._drive.download_file(access_token=access_token, file_id=file.provider_file_id)

    def _fail_archive_step(
        self, job: ExecutionJob, plan: ExecutionPlan, step: ExecutionStep, error: str
    ) -> None:
        now = datetime.now(UTC)
        self._steps.mark_failed(step)
        self._results.create(
            execution_job_id=job.id,
            execution_step_id=step.id,
            status=ExecutionResultStatus.FAILED,
            verification_status=VerificationStatus.SKIPPED,
            error=error,
            executed_at=now,
            verified_at=None,
        )
        self._audits.record(
            organization_id=plan.organization_id,
            execution_plan_id=plan.id,
            execution_job_id=job.id,
            event_type="step_failed",
            message=error,
            metadata={"execution_step_id": str(step.id), "action_type": step.action_type},
        )

    def _execute_archive_batch(
        self,
        job: ExecutionJob,
        plan: ExecutionPlan,
        steps: list[ExecutionStep],
        *,
        access_token: str,
    ) -> None:
        """Completes every `CREATE_ARCHIVE` step in `steps` together as one
        zip → object-storage write, not independently. Per-file problems
        (missing file, oversized, unexportable type, fetch error) fail only
        that one step and continue; a failure in the shared part of the
        operation (nothing left to archive, or the object-storage write
        itself) fails the whole batch as a group — see the except block
        below for why that's `rollback()`-then-refail rather than leaving
        already-failed steps alone."""
        settings = get_settings()
        archive_job = self._archive_jobs.get_by_plan_id(plan.id) or self._archive_jobs.create(
            organization_id=plan.organization_id,
            execution_plan_id=plan.id,
            name=f"Archive - {plan.estimated_impact}",
            created_by_user_id=plan.created_by_user_id,
        )
        self._archive_jobs.mark_creating(archive_job)
        self._db.commit()

        manifest: list[dict] = []
        included_steps: list[ExecutionStep] = []
        buffer = tempfile.SpooledTemporaryFile(max_size=64 * 1024 * 1024)
        try:
            try:
                with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    used_names: set[str] = set()
                    for step in steps:
                        file = self._files.get_by_id(step.target_file_id)
                        if file is None:
                            self._fail_archive_step(
                                job,
                                plan,
                                step,
                                "Target file no longer exists in this platform's inventory.",
                            )
                            continue
                        if (file.size_bytes or 0) > settings.archive_max_file_size_bytes:
                            self._fail_archive_step(job, plan, step, "File is too large to archive.")
                            continue

                        try:
                            content = self._fetch_file_bytes(file, access_token=access_token)
                        except Exception as exc:  # noqa: BLE001 - one file's fetch failure must not stop the batch
                            self._fail_archive_step(job, plan, step, str(exc))
                            continue
                        if content is None:
                            self._fail_archive_step(job, plan, step, "This file type can't be archived.")
                            continue

                        zip_name = file.name
                        suffix = 1
                        while zip_name in used_names:
                            suffix += 1
                            zip_name = f"{file.name} ({suffix})"
                        used_names.add(zip_name)

                        zip_file.writestr(zip_name, content)
                        manifest.append(
                            {
                                "file_id": str(file.id),
                                "name": file.name,
                                "path": file.path,
                                "size_bytes": len(content),
                                "mime_type": file.mime_type,
                                "checksum_sha256": hashlib.sha256(content).hexdigest(),
                            }
                        )
                        included_steps.append(step)

                if not manifest:
                    raise ValidationError("No selected file could be included in the archive.")

                original_size = sum(entry["size_bytes"] for entry in manifest)
                # boto3's upload_fileobj closes the passed file object once
                # the transfer completes — compressed_size has to be read
                # *before* that call, not after; put_object must be the
                # last thing this method ever does to `buffer`.
                compressed_size = buffer.seek(0, 2)
                buffer.seek(0)
                key = f"archives/{plan.organization_id}/{plan.id}.zip"
                self._object_storage.put_object(
                    key=key, body=buffer, content_type="application/zip"
                )
            except Exception as exc:  # noqa: BLE001 - archive-batch boundary must never crash the worker
                logger.exception("archive_batch_failed", extra={"execution_plan_id": str(plan.id)})
                # rollback() expires every object in the session, so any
                # individual _fail_archive_step calls already flushed above
                # (but never committed) are undone too — every step in
                # `steps` reads back as PENDING again here. That's the
                # desired failure semantics for this action type: one
                # object-storage write failing after some files fetched
                # fine should fail the whole batch together, not partially
                # (see docstring above on _execute_archive_batch).
                self._db.rollback()
                self._archive_jobs.mark_failed(archive_job)
                for step in steps:
                    self._fail_archive_step(job, plan, step, str(exc))
                self._db.commit()
                return
        finally:
            buffer.close()

        self._archive_jobs.mark_completed(
            archive_job,
            object_storage_key=key,
            original_size_bytes=original_size,
            compressed_size_bytes=compressed_size,
            file_count=len(manifest),
            manifest=manifest,
        )

        now = datetime.now(UTC)
        for step in included_steps:
            self._rollback_records.create(
                execution_step_id=step.id, pre_state={"archive_job_id": str(archive_job.id)}
            )
            self._steps.mark_completed(step)
            self._results.create(
                execution_job_id=job.id,
                execution_step_id=step.id,
                status=ExecutionResultStatus.SUCCESS,
                verification_status=VerificationStatus.VERIFIED,
                error=None,
                executed_at=now,
                verified_at=now,
            )
            self._audits.record(
                organization_id=plan.organization_id,
                execution_plan_id=plan.id,
                execution_job_id=job.id,
                event_type="step_completed",
                metadata={
                    "execution_step_id": str(step.id),
                    "action_type": step.action_type,
                    "archive_job_id": str(archive_job.id),
                },
            )
        self._db.commit()

    def _verify_forward(self, step: ExecutionStep, *, access_token: str, file: File) -> bool:
        current = self._drive.get_file(access_token=access_token, file_id=file.provider_file_id)
        if step.action_type in _TRASHABLE_ACTIONS:
            return current.trashed is True
        if step.action_type == ExecutionActionType.RENAME:
            expected = step.planned_change.get("new_name")
            return expected is None or current.name == expected
        if step.action_type in _MOVE_ACTIONS:
            expected = step.planned_change.get("new_parent_id")
            return expected is None or expected in current.parents
        return True

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def _run_rollback(self, job: ExecutionJob, plan: ExecutionPlan, *, access_token: str) -> None:
        records = self._rollback_records.list_rollbackable_for_plan(plan.id)
        succeeded = 0
        failed = 0
        trashable_restored = False
        for record in records:
            self._check_cancelled(job.id)
            if self._jobs.is_pause_requested(job.id):
                self._jobs.mark_paused(job)
                self._audits.record(
                    organization_id=plan.organization_id,
                    execution_plan_id=plan.id,
                    execution_job_id=job.id,
                    event_type="execution_paused",
                )
                self._db.commit()
                raise ExecutionPaused

            step = self._steps.get_by_id(record.execution_step_id)
            if step is None:
                failed += 1
                continue

            if self._rollback_one(job, plan, step, record, access_token=access_token):
                succeeded += 1
                if step.action_type in _TRASHABLE_ACTIONS:
                    trashable_restored = True
            else:
                failed += 1

        if failed == 0 and succeeded > 0:
            self._jobs.mark_completed(job)
            self._plans.update_status(plan, status=ExecutionPlanStatus.ROLLED_BACK)
        elif succeeded == 0:
            self._jobs.mark_failed(job, error="All rollback steps failed.")
        else:
            self._jobs.mark_partially_completed(job)

        self._audits.record(
            organization_id=plan.organization_id,
            execution_plan_id=plan.id,
            execution_job_id=job.id,
            event_type="execution_rollback_completed",
            metadata={"succeeded": succeeded, "failed": failed},
        )
        self._db.commit()

        # Un-trashing restores the file to active storage — the totals need
        # to come back up, same as they needed to go down when it was
        # trashed in the first place.
        if trashable_restored:
            self._trigger_storage_refresh(plan.organization_id)

    def _rollback_one(
        self,
        job: ExecutionJob,
        plan: ExecutionPlan,
        step: ExecutionStep,
        record: RollbackRecord,
        *,
        access_token: str,
    ) -> bool:
        now = datetime.now(UTC)
        try:
            file = self._files.get_by_id(step.target_file_id)
            if file is None:
                raise NotFoundError("Target file no longer exists in this platform's inventory.")

            self._apply_rollback(
                step.action_type, access_token=access_token, file=file, pre_state=record.pre_state
            )
            self._rollback_records.mark_rolled_back(record, user_id=job.triggered_by_user_id)
            self._steps.mark_rolled_back(step)
        except Exception as exc:  # noqa: BLE001 - one file's rollback failure must not stop the rest
            logger.exception(
                "execution_rollback_step_failed", extra={"execution_step_id": str(step.id)}
            )
            self._db.rollback()
            self._results.create(
                execution_job_id=job.id,
                execution_step_id=step.id,
                status=ExecutionResultStatus.FAILED,
                verification_status=VerificationStatus.SKIPPED,
                error=str(exc),
                executed_at=now,
                verified_at=None,
            )
            self._audits.record(
                organization_id=plan.organization_id,
                execution_plan_id=plan.id,
                execution_job_id=job.id,
                event_type="rollback_step_failed",
                message=str(exc),
                metadata={"execution_step_id": str(step.id)},
            )
            self._db.commit()
            return False

        self._results.create(
            execution_job_id=job.id,
            execution_step_id=step.id,
            status=ExecutionResultStatus.SUCCESS,
            verification_status=VerificationStatus.VERIFIED,
            error=None,
            executed_at=now,
            verified_at=datetime.now(UTC),
        )
        self._audits.record(
            organization_id=plan.organization_id,
            execution_plan_id=plan.id,
            execution_job_id=job.id,
            event_type="rollback_step_completed",
            metadata={"execution_step_id": str(step.id)},
        )
        self._db.commit()
        return True

    def _apply_rollback(
        self, action_type: str, *, access_token: str, file: File, pre_state: dict
    ) -> None:
        if action_type in _TRASHABLE_ACTIONS:
            self._drive.set_trashed(
                access_token=access_token, file_id=file.provider_file_id, trashed=False
            )
            self._files.mark_trashed(file, trashed=False)
        elif action_type == ExecutionActionType.RENAME:
            self._drive.rename_file(
                access_token=access_token,
                file_id=file.provider_file_id,
                new_name=pre_state["name"],
            )
        elif action_type in _MOVE_ACTIONS:
            current = self._drive.get_file(access_token=access_token, file_id=file.provider_file_id)
            current_parent_id = current.parents[0] if current.parents else None
            original_parent_id = pre_state.get("parent_folder_id")
            if not current_parent_id or not original_parent_id:
                raise ValidationError("Cannot determine parents to reverse this move.")
            self._drive.move_file(
                access_token=access_token,
                file_id=file.provider_file_id,
                add_parent_id=original_parent_id,
                remove_parent_id=current_parent_id,
            )
        elif action_type == ExecutionActionType.UPDATE_METADATA:
            self._drive.update_app_properties(
                access_token=access_token,
                file_id=file.provider_file_id,
                properties=pre_state.get("app_properties", {}),
            )
        elif action_type == ExecutionActionType.CREATE_ARCHIVE:
            # No Drive call — CREATE_ARCHIVE never mutated Drive, only read
            # it, so `file` isn't touched here at all.
            self._rollback_archive(pre_state["archive_job_id"])
        else:
            raise ValidationError(f"Unsupported action type: {action_type}")

    def _rollback_archive(self, archive_job_id: str) -> None:
        """Every sibling `CREATE_ARCHIVE` step in a plan shares one
        `ArchiveJob`, so this runs once per step during a plan rollback —
        idempotent via the status check, since the object is only ever
        deleted once."""
        archive_job = self._archive_jobs.get_by_id(uuid.UUID(archive_job_id))
        if archive_job is None or archive_job.status != ArchiveJobStatus.COMPLETED:
            return
        if archive_job.object_storage_key:
            self._object_storage.delete_object(key=archive_job.object_storage_key)
        self._archive_jobs.mark_failed(archive_job)

    def _check_cancelled(self, execution_job_id: uuid.UUID) -> None:
        if self._jobs.is_cancel_requested(execution_job_id):
            raise ExecutionCancelled

    def _trigger_storage_refresh(self, organization_id: uuid.UUID) -> None:
        """A trash (or its rollback) just changed which files count toward
        active storage — without this, Storage Intelligence's totals and
        the Dashboard's `total_storage_bytes` would keep reporting the
        pre-trash number until the next scan or manual re-analysis (see
        `File.trashed`'s docstring). Mirrors the exact enqueue-guarded-by-
        has_active_job pattern `worker.tasks.scan`/`worker.tasks.embedding`
        already use for their own completion-chained triggers — a failure
        to enqueue either (e.g. one already running) is not itself a
        problem worth failing the execution job over, so both are best-
        effort here."""
        if not self._storage_analysis_jobs.has_active_job(organization_id):
            analysis_job = self._storage_analysis_jobs.create(
                organization_id=organization_id,
                triggered_by=StorageAnalysisTrigger.EXECUTION_COMPLETED,
                triggered_by_user_id=None,
            )
            self._db.commit()
            run_storage_intelligence.delay(str(analysis_job.id))

        if not self._recommendation_jobs.has_active_job(organization_id):
            recommendation_job = self._recommendation_jobs.create(
                organization_id=organization_id,
                triggered_by=RecommendationTrigger.EXECUTION_COMPLETED,
                triggered_by_user_id=None,
            )
            self._db.commit()
            run_recommendation.delay(str(recommendation_job.id))
