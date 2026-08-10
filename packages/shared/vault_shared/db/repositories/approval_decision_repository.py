import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import ApprovalDecision


class ApprovalDecisionRepository:
    """Append-only — an `ApprovalDecision`, once recorded, is never updated
    or deleted (Handbook §13's "audit logs are append-only"). Two creation
    methods, not one signature with an optional user (Phase 9, ADR-021):
    `create` is the unchanged human-decision path from Phase 8; `
    create_by_policy` is the new policy-attributed path — keeping them
    distinct in code makes the two decision "shapes" explicit rather than
    relying on which optional argument happened to be passed."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        approval_request_id: uuid.UUID,
        decider_user_id: uuid.UUID,
        decision: str,
        comments: str | None,
        ip_address: str | None,
    ) -> ApprovalDecision:
        record = ApprovalDecision(
            approval_request_id=approval_request_id,
            decider_user_id=decider_user_id,
            decision=decision,
            comments=comments,
            ip_address=ip_address,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def create_by_policy(
        self,
        *,
        approval_request_id: uuid.UUID,
        decided_by_policy_id: uuid.UUID,
        decision: str,
        comments: str | None = None,
    ) -> ApprovalDecision:
        record = ApprovalDecision(
            approval_request_id=approval_request_id,
            decided_by_policy_id=decided_by_policy_id,
            decision=decision,
            comments=comments,
            ip_address=None,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def list_for_request(self, approval_request_id: uuid.UUID) -> list[ApprovalDecision]:
        return (
            self._session.query(ApprovalDecision)
            .filter_by(approval_request_id=approval_request_id)
            .order_by(ApprovalDecision.created_at)
            .all()
        )
