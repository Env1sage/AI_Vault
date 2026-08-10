import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from vault_shared.execution.permission_validation import validate_execution_permissions
from vault_shared import ConflictError, NotFoundError, ValidationError, VaultError
from vault_shared.db.models import (
    ApprovalDecisionType,
    ApprovalRequest,
    ApprovalStatus,
    ExecutionPlan,
    ExecutionPlanStatus,
    StorageConnector,
)
from vault_shared.db.repositories import (
    ApprovalDecisionRepository,
    ApprovalRequestRepository,
    AuditLogRepository,
    ConnectorCredentialsRepository,
    ExecutionAuditRepository,
    ExecutionJobRepository,
    ExecutionPlanRepository,
    StorageConnectorRepository,
)

_EVENT_TYPE_BY_DECISION = {
    ApprovalDecisionType.APPROVE: "execution_approved",
    ApprovalDecisionType.REJECT: "execution_rejected",
    ApprovalDecisionType.REQUEST_CHANGES: "execution_changes_requested",
}
_PLAN_STATUS_BY_DECISION = {
    ApprovalDecisionType.APPROVE: ExecutionPlanStatus.APPROVED,
    ApprovalDecisionType.REJECT: ExecutionPlanStatus.REJECTED,
    ApprovalDecisionType.REQUEST_CHANGES: ExecutionPlanStatus.CHANGES_REQUESTED,
}
_APPROVAL_STATUS_BY_DECISION = {
    ApprovalDecisionType.APPROVE: ApprovalStatus.APPROVED,
    ApprovalDecisionType.REJECT: ApprovalStatus.REJECTED,
    ApprovalDecisionType.REQUEST_CHANGES: ApprovalStatus.CHANGES_REQUESTED,
}


class ApprovalService:
    """The Approval System (Phase 8 spec, Handbook §13's "Approval
    workflow for destructive actions... explicit human approval captured
    before execution"). `decide()` is the single choke point every
    execution passes through — only an `approve` decision that also
    passes `validate_execution_permissions` creates an `ExecutionJob`
    and enqueues it; `reject`/`request_changes` are terminal for this
    plan. The enqueue side effect is constructor-injected rather than
    importing the Celery producer module directly, so this service stays
    trivially unit-testable without touching Redis."""

    def __init__(self, db: Session, *, enqueue_execution_job: Callable[[uuid.UUID], None]) -> None:
        self._db = db
        self._approvals = ApprovalRequestRepository(db)
        self._decisions = ApprovalDecisionRepository(db)
        self._plans = ExecutionPlanRepository(db)
        self._jobs = ExecutionJobRepository(db)
        self._connectors = StorageConnectorRepository(db)
        self._credentials = ConnectorCredentialsRepository(db)
        self._execution_audits = ExecutionAuditRepository(db)
        self._audit_logs = AuditLogRepository(db)
        self._enqueue_execution_job = enqueue_execution_job

    def list_for_organization(
        self, organization_id: uuid.UUID, *, status: str | None = None
    ) -> list[ApprovalRequest]:
        requests = self._approvals.list_for_organization(organization_id, status=status)
        return [self._approvals.expire_if_overdue(request) for request in requests]

    def get_owned(
        self, approval_request_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> ApprovalRequest:
        request = self._approvals.get_owned(approval_request_id, organization_id=organization_id)
        if request is None:
            raise NotFoundError("Approval request not found.")
        return self._approvals.expire_if_overdue(request)

    def decide(
        self,
        approval_request_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        decision: str,
        comments: str | None,
        ip_address: str | None,
    ) -> ApprovalRequest:
        request = self.get_owned(approval_request_id, organization_id=organization_id)
        if request.status != ApprovalStatus.PENDING:
            raise ConflictError(f"This approval request is already {request.status}.")

        plan = self._plans.get_by_id(request.execution_plan_id)
        if plan is None:
            raise NotFoundError("Execution plan not found.")
        if decision == ApprovalDecisionType.APPROVE:
            self._check_permissions(plan, organization_id=organization_id)

        self._decisions.create(
            approval_request_id=request.id,
            decider_user_id=user_id,
            decision=decision,
            comments=comments,
            ip_address=ip_address,
        )
        self._approvals.mark_status(request, status=_APPROVAL_STATUS_BY_DECISION[decision])
        self._plans.update_status(plan, status=_PLAN_STATUS_BY_DECISION[decision])

        job = None
        if decision == ApprovalDecisionType.APPROVE:
            job = self._jobs.create(
                execution_plan_id=plan.id,
                organization_id=organization_id,
                triggered_by_user_id=user_id,
            )

        self._execution_audits.record(
            organization_id=organization_id,
            execution_plan_id=plan.id,
            execution_job_id=job.id if job else None,
            actor_user_id=user_id,
            event_type=_EVENT_TYPE_BY_DECISION[decision],
            message=comments,
        )
        self._audit_logs.record(
            event_type=_EVENT_TYPE_BY_DECISION[decision],
            organization_id=organization_id,
            user_id=user_id,
            ip_address=ip_address,
            metadata={
                "approval_request_id": str(request.id),
                "execution_plan_id": str(plan.id),
            },
        )
        self._db.commit()

        if job is not None:
            self._enqueue_execution_job(job.id)
        return request

    def bulk_decide(
        self,
        approval_request_ids: list[uuid.UUID],
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        decision: str,
        comments: str | None,
        ip_address: str | None,
    ) -> list[ApprovalRequest]:
        """One bad id in the batch must not block the rest — same per-item
        failure isolation every job-processing loop in this codebase has
        used since Phase 4."""
        decided = []
        for request_id in approval_request_ids:
            try:
                decided.append(
                    self.decide(
                        request_id,
                        organization_id=organization_id,
                        user_id=user_id,
                        decision=decision,
                        comments=comments,
                        ip_address=ip_address,
                    )
                )
            except VaultError:
                continue
        return decided

    def _check_permissions(self, plan: ExecutionPlan, *, organization_id: uuid.UUID) -> None:
        connector = self._resolve_connector(plan, organization_id=organization_id)
        credentials = self._credentials.get_by_connector_id(connector.id) if connector else None
        failures = validate_execution_permissions(connector=connector, credentials=credentials)
        if failures:
            raise ValidationError(
                "Cannot approve — execution permissions are not satisfied: "
                + "; ".join(failures)
            )

    def _resolve_connector(
        self, plan: ExecutionPlan, *, organization_id: uuid.UUID
    ) -> StorageConnector | None:
        return self._connectors.get_by_organization_and_provider(
            organization_id=organization_id, provider=plan.target_provider
        )
