import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from vault_shared import ConflictError, NotFoundError, ValidationError, get_settings
from vault_shared.db.models import (
    ExecutionActionType,
    ExecutionPlan,
    ExecutionStep,
    File,
    RecommendationRiskLevel,
    RecommendationStatus,
)
from vault_shared.db.repositories import (
    ApprovalRequestRepository,
    AuditLogRepository,
    DuplicateGroupRepository,
    ExecutionAuditRepository,
    ExecutionPlanRepository,
    ExecutionStepRepository,
    FileRepository,
    RecommendationRepository,
)
from vault_shared.formatting import human_bytes

# Only these Phase 7 rules map to a Phase 8-supported action type — every
# other rule (security/collaboration/productivity/knowledge findings) has
# no concrete, safe storage mutation behind it yet. `create_plan` rejects
# any other rule_name with a clear `ValidationError` rather than silently
# doing nothing.
_EXECUTABLE_RULES: dict[str, str] = {
    "duplicate_files": ExecutionActionType.REMOVE_DUPLICATE,
    "archive_candidates": ExecutionActionType.ARCHIVE,
    "large_unused_files": ExecutionActionType.ARCHIVE,
}

# Storage Intelligence's ad-hoc plans (large/old/inactive/temporary-
# candidate listings, where the user picks specific files directly rather
# than acting on a precomputed group) are deliberately restricted to a
# narrow allowlist — the same philosophy as `_EXECUTABLE_RULES` (ADR-020).
# ARCHIVE (Drive Trash) is reversible; CREATE_ARCHIVE (Archive MVP) never
# mutates Drive at all, only reads. RENAME/MOVE_FILE are the Files browser's
# real file-explorer operations (each needs its own `new_name`/
# `new_parent_id` parameter, validated in `create_ad_hoc_plan`).
# UPDATE_METADATA/MOVE_FOLDER have no caller yet and stay unreachable.
_AD_HOC_ALLOWED_ACTIONS = frozenset(
    {
        ExecutionActionType.ARCHIVE,
        ExecutionActionType.CREATE_ARCHIVE,
        ExecutionActionType.RENAME,
        ExecutionActionType.MOVE_FILE,
    }
)
_MAX_AD_HOC_FILES = 500

# Execution risk is a different question than the recommendation's own
# risk_level (which describes the *business* risk of the underlying
# storage/security issue) — every action this phase supports is fully
# reversible (Drive Trash, not deletion), so execution risk is really
# about blast radius: how many files does one approval affect at once.
_RISK_LOW_MAX_FILES = 10
_RISK_MEDIUM_MAX_FILES = 100


@dataclass(frozen=True)
class ExecutionPlanDetail:
    plan: ExecutionPlan
    steps: list[ExecutionStep]


class ExecutionPlanService:
    """The Execution Planner (Phase 8 spec) — converts one `Recommendation`
    into a deterministic, reviewable `ExecutionPlan` plus its
    `ApprovalRequest`. Reads only already-stored `File`/`Recommendation`
    state; makes no Drive call and mutates nothing outside this
    platform's own database — the Core Philosophy's lifecycle has no
    state where a plan exists without a pending approval, so both are
    always created in the same transaction.

    Lives in `packages/shared`, not `apps/backend`, since Phase 9's
    `EXECUTE_ACTION` workflow node (`apps/worker/worker/workflow/`) needs
    to build plans too, not just the backend's `POST /v1/execution-plans`
    endpoint — same "promote to packages/shared once a second app needs
    it" reasoning ADR-015 used for the DB layer ahead of Phase 4.
    `apps/backend/app/application/execution_plan_service.py` re-exports
    this class unchanged so no backend caller needed to change."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._recommendations = RecommendationRepository(db)
        self._duplicate_groups = DuplicateGroupRepository(db)
        self._plans = ExecutionPlanRepository(db)
        self._steps = ExecutionStepRepository(db)
        self._approvals = ApprovalRequestRepository(db)
        self._files = FileRepository(db)
        self._execution_audits = ExecutionAuditRepository(db)
        self._audit_logs = AuditLogRepository(db)

    def create_plan(
        self, recommendation_id: uuid.UUID, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> ExecutionPlan:
        recommendation = self._recommendations.get_owned(
            recommendation_id, organization_id=organization_id
        )
        if recommendation is None:
            raise NotFoundError("Recommendation not found.")
        if recommendation.status != RecommendationStatus.ACTIVE:
            raise ConflictError("Only active recommendations can be turned into an execution plan.")

        action_type = _EXECUTABLE_RULES.get(recommendation.rule_name)
        if action_type is None:
            raise ValidationError(
                f"Recommendations from rule '{recommendation.rule_name}' have no supported "
                "execution action yet — this category is view-only for now."
            )
        if self._plans.has_active_plan_for_recommendation(recommendation_id):
            raise ConflictError(
                "An execution plan is already pending or in progress for this recommendation."
            )

        file_ids = [uuid.UUID(fid) for fid in recommendation.affected_file_ids]
        files_by_id = {f.id: f for f in self._files.list_by_ids(file_ids)}
        ordered_files = [files_by_id[fid] for fid in file_ids if fid in files_by_id]
        if not ordered_files:
            raise ValidationError(
                "None of this recommendation's affected files could be found — it may be "
                "stale. Refresh recommendations and try again."
            )

        return self._create_plan_with_approval(
            organization_id=organization_id,
            user_id=user_id,
            recommendation_id=recommendation_id,
            duplicate_group_id=None,
            action_type=action_type,
            ordered_files=ordered_files,
            audit_metadata={"recommendation_id": str(recommendation_id)},
        )

    def create_plan_from_duplicate_group(
        self, duplicate_group_id: uuid.UUID, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> ExecutionPlan:
        """Storage Intelligence's (post-hardening) equivalent of `create_plan`
        — a `DuplicateGroup` is already a concrete, content-verified set of
        exact-duplicate files (ADR-023's checksum `GROUP BY`, not a
        filename heuristic), so unlike a `Recommendation` there is no
        rule-name allowlist to check: every duplicate group is executable
        by construction. Only the non-`is_recommended_keep` members become
        `REMOVE_DUPLICATE` steps — the recommended copy is always left
        alone. See ADR-024."""
        group = self._duplicate_groups.get_owned(
            duplicate_group_id, organization_id=organization_id
        )
        if group is None:
            raise NotFoundError("Duplicate group not found.")
        if self._plans.has_active_plan_for_duplicate_group(duplicate_group_id):
            raise ConflictError(
                "An execution plan is already pending or in progress for this duplicate group."
            )

        members = self._duplicate_groups.list_members_with_files(duplicate_group_id)
        ordered_files = [file for member, file in members if not member.is_recommended_keep]
        if not ordered_files:
            raise ValidationError(
                "This duplicate group has no removable copies — it may be stale. "
                "Re-analyze storage and try again."
            )

        return self._create_plan_with_approval(
            organization_id=organization_id,
            user_id=user_id,
            recommendation_id=None,
            duplicate_group_id=duplicate_group_id,
            action_type=ExecutionActionType.REMOVE_DUPLICATE,
            ordered_files=ordered_files,
            audit_metadata={"duplicate_group_id": str(duplicate_group_id)},
        )

    def create_ad_hoc_plan(
        self,
        file_ids: list[uuid.UUID],
        *,
        action_type: str,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        new_name: str | None = None,
        new_parent_id: str | None = None,
    ) -> ExecutionPlan:
        """Storage Intelligence's large/old/inactive/temporary-candidate
        listings are live queries, not precomputed groups (ADR-023) — there
        is no `DuplicateGroup`-shaped row to originate a plan from, only the
        set of file ids the user picked on that listing page. Restricted to
        `_AD_HOC_ALLOWED_ACTIONS` and re-verifies every id actually belongs
        to this organization via `FileRepository.list_owned_by_organization`
        — unlike the other two `create_plan*` methods, nothing upstream
        already guaranteed that for a caller-supplied id list.

        `new_name`/`new_parent_id` are the Files browser's real
        file-explorer operations' one extra parameter each: a `RENAME` plan
        always targets exactly one file (renaming N files to the same
        literal string has no sensible meaning), while `MOVE_FILE` moves
        every selected file to the same destination folder."""
        if action_type not in _AD_HOC_ALLOWED_ACTIONS:
            raise ValidationError(f"'{action_type}' is not a supported ad-hoc action.")
        if not file_ids:
            raise ValidationError("Select at least one file.")
        if len(file_ids) > _MAX_AD_HOC_FILES:
            raise ValidationError(f"Select at most {_MAX_AD_HOC_FILES} files at a time.")
        if action_type == ExecutionActionType.RENAME:
            if len(file_ids) != 1:
                raise ValidationError("Rename one file at a time.")
            if not new_name or not new_name.strip():
                raise ValidationError("A new name is required.")
        if action_type == ExecutionActionType.MOVE_FILE and not new_parent_id:
            raise ValidationError("A destination folder is required.")

        ordered_files = self._files.list_owned_by_organization(
            file_ids, organization_id=organization_id
        )
        if not ordered_files:
            raise ValidationError(
                "None of the selected files could be found — they may be stale. "
                "Refresh and try again."
            )

        planned_change_by_file_id: dict[uuid.UUID, dict] | None = None
        if action_type == ExecutionActionType.RENAME:
            planned_change_by_file_id = {
                ordered_files[0].id: {"action": action_type, "new_name": new_name.strip()}
            }
        elif action_type == ExecutionActionType.MOVE_FILE:
            planned_change_by_file_id = {
                file.id: {"action": action_type, "new_parent_id": new_parent_id}
                for file in ordered_files
            }

        return self._create_plan_with_approval(
            organization_id=organization_id,
            user_id=user_id,
            recommendation_id=None,
            duplicate_group_id=None,
            action_type=action_type,
            ordered_files=ordered_files,
            audit_metadata={"ad_hoc_action": action_type, "requested_file_count": len(file_ids)},
            planned_change_by_file_id=planned_change_by_file_id,
        )

    def _create_plan_with_approval(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        recommendation_id: uuid.UUID | None,
        duplicate_group_id: uuid.UUID | None,
        action_type: str,
        ordered_files: list[File],
        audit_metadata: dict,
        planned_change_by_file_id: dict[uuid.UUID, dict] | None = None,
    ) -> ExecutionPlan:
        total_bytes = sum(f.size_bytes or 0 for f in ordered_files)
        plan = self._plans.create(
            organization_id=organization_id,
            recommendation_id=recommendation_id,
            duplicate_group_id=duplicate_group_id,
            created_by_user_id=user_id,
            target_provider="google_workspace",
            estimated_impact=f"{len(ordered_files)} files, ~{human_bytes(total_bytes)}",
            estimated_storage_savings_bytes=total_bytes or None,
            risk_level=self._risk_level_for(len(ordered_files)),
            rollback_available=True,
            required_permissions=["google_workspace:drive:write"],
        )
        for index, file in enumerate(ordered_files):
            planned_change = (planned_change_by_file_id or {}).get(
                file.id, {"action": action_type}
            )
            self._steps.create(
                execution_plan_id=plan.id,
                step_order=index,
                action_type=action_type,
                target_file_id=file.id,
                pre_state=self._pre_state(file),
                planned_change=planned_change,
            )

        settings = get_settings()
        expires_at = datetime.now(UTC) + timedelta(hours=settings.approval_expiry_hours)
        self._approvals.create(
            execution_plan_id=plan.id,
            organization_id=organization_id,
            requested_by_user_id=user_id,
            expires_at=expires_at,
        )

        self._execution_audits.record(
            organization_id=organization_id,
            execution_plan_id=plan.id,
            actor_user_id=user_id,
            event_type="execution_plan_created",
            metadata={**audit_metadata, "step_count": len(ordered_files)},
        )
        self._audit_logs.record(
            event_type="execution_plan_created",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"execution_plan_id": str(plan.id)},
        )
        self._db.commit()
        return plan

    def get_detail(
        self, execution_plan_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> ExecutionPlanDetail:
        plan = self._plans.get_owned(execution_plan_id, organization_id=organization_id)
        if plan is None:
            raise NotFoundError("Execution plan not found.")
        return ExecutionPlanDetail(plan=plan, steps=self._steps.list_for_plan(plan.id))

    def list_for_organization(
        self, organization_id: uuid.UUID, *, status: str | None = None
    ) -> list[ExecutionPlan]:
        return self._plans.list_for_organization(organization_id, status=status)

    @staticmethod
    def _risk_level_for(file_count: int) -> str:
        if file_count <= _RISK_LOW_MAX_FILES:
            return RecommendationRiskLevel.LOW
        if file_count <= _RISK_MEDIUM_MAX_FILES:
            return RecommendationRiskLevel.MEDIUM
        return RecommendationRiskLevel.HIGH

    @staticmethod
    def _pre_state(file: File) -> dict:
        return {
            "parent_folder_id": str(file.parent_folder_id) if file.parent_folder_id else None,
            "name": file.name,
        }
