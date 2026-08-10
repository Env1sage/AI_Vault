import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared import ConflictError, NotFoundError, ValidationError, get_logger
from vault_shared.connector_service import ConnectorTokenService
from vault_shared.connectors.google_drive import DriveFile, GoogleDriveClient
from vault_shared.connectors.google_workspace import GoogleWorkspaceOAuthClient
from vault_shared.db.models import (
    ExecutionActionType,
    ExecutionJob,
    ExecutionPlan,
    ExecutionPlanStatus,
    ExecutionResultStatus,
    ExecutionStep,
    ExecutionStepStatus,
    File,
    RollbackRecord,
    VerificationStatus,
)
from vault_shared.db.repositories import (
    ConnectorCredentialsRepository,
    ExecutionAuditRepository,
    ExecutionJobRepository,
    ExecutionPlanRepository,
    ExecutionResultRepository,
    ExecutionStepRepository,
    FileRepository,
    RollbackRecordRepository,
    StorageConnectorRepository,
)
from vault_shared.execution import validate_execution_permissions

logger = get_logger("worker.execution.execution_service")

_TRASHABLE_ACTIONS = (ExecutionActionType.ARCHIVE, ExecutionActionType.REMOVE_DUPLICATE)
_MOVE_ACTIONS = (ExecutionActionType.MOVE_FILE, ExecutionActionType.MOVE_FOLDER)


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
    ) -> None:
        self._db = db
        self._drive = drive_client
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
        else:
            raise ValidationError(f"Unsupported action type: {action_type}")

    def _check_cancelled(self, execution_job_id: uuid.UUID) -> None:
        if self._jobs.is_cancel_requested(execution_job_id):
            raise ExecutionCancelled
