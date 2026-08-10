import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import ApprovalRequest, ApprovalStatus


class ApprovalRequestRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        requested_by_user_id: uuid.UUID,
        expires_at: datetime,
        execution_plan_id: uuid.UUID | None = None,
        workflow_node_execution_id: uuid.UUID | None = None,
    ) -> ApprovalRequest:
        """Exactly one of `execution_plan_id`/`workflow_node_execution_id`
        must be provided (Phase 9, ADR-021) — enforced by a DB CHECK
        constraint, not just this signature."""
        request = ApprovalRequest(
            execution_plan_id=execution_plan_id,
            workflow_node_execution_id=workflow_node_execution_id,
            organization_id=organization_id,
            requested_by_user_id=requested_by_user_id,
            expires_at=expires_at,
        )
        self._session.add(request)
        self._session.flush()
        return request

    def get_by_id(self, approval_request_id: uuid.UUID) -> ApprovalRequest | None:
        return self._session.get(ApprovalRequest, approval_request_id)

    def get_owned(
        self, approval_request_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> ApprovalRequest | None:
        return (
            self._session.query(ApprovalRequest)
            .filter_by(id=approval_request_id, organization_id=organization_id)
            .first()
        )

    def get_by_plan(self, execution_plan_id: uuid.UUID) -> ApprovalRequest | None:
        return (
            self._session.query(ApprovalRequest)
            .filter_by(execution_plan_id=execution_plan_id)
            .first()
        )

    def get_by_workflow_node_execution(
        self, workflow_node_execution_id: uuid.UUID
    ) -> ApprovalRequest | None:
        return (
            self._session.query(ApprovalRequest)
            .filter_by(workflow_node_execution_id=workflow_node_execution_id)
            .first()
        )

    def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ApprovalRequest]:
        query = self._session.query(ApprovalRequest).filter_by(organization_id=organization_id)
        if status is not None:
            query = query.filter(ApprovalRequest.status == status)
        return (
            query.order_by(ApprovalRequest.created_at.desc()).limit(limit).offset(offset).all()
        )

    def mark_status(self, request: ApprovalRequest, *, status: str) -> None:
        request.status = status
        self._session.flush()

    def expire_if_overdue(self, request: ApprovalRequest) -> ApprovalRequest:
        """Lazy expiry, checked whenever a request is read — the same
        self-healing pattern every prior phase's resumable "pending" query
        used. Still lazy even now that Phase 9 adds a real scheduler: the
        scheduler's own periodic sweep is for firing workflow triggers, not
        a generic background-expiry job, so this stays the simplest correct
        mechanism rather than growing a second, redundant sweep."""
        if request.status == ApprovalStatus.PENDING and datetime.now(UTC) > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            self._session.flush()
        return request
