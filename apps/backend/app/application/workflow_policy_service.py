import uuid

from sqlalchemy.orm import Session

from vault_shared import NotFoundError, ValidationError
from vault_shared.db.models import WorkflowPolicy, WorkflowPolicyEffect
from vault_shared.db.repositories import AuditLogRepository, WorkflowPolicyRepository

_VALID_EFFECTS = {member.value for member in WorkflowPolicyEffect}


class WorkflowPolicyService:
    """The Policy Engine's CRUD surface (Phase 9 spec: "Policies determine
    execution behavior... must be versioned and auditable"). Every edit is
    a brand-new row, never an in-place update — `WorkflowPolicyRepository.
    create_draft` always appends the next version number for a
    `(organization_id, policy_key)` pair, so a policy's full history is
    retained even after it's edited or archived. Publishing is required
    before an `EXECUTE_ACTION` node can actually use a policy — a draft
    can be reviewed and discarded without ever affecting a live workflow.
    See ADR-021."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._policies = WorkflowPolicyRepository(db)
        self._audit_logs = AuditLogRepository(db)

    def create_draft(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        policy_key: str,
        name: str,
        description: str | None,
        effect: str,
        conditions: dict,
    ) -> WorkflowPolicy:
        if effect not in _VALID_EFFECTS:
            raise ValidationError(f"Unknown policy effect: {effect}")

        policy = self._policies.create_draft(
            organization_id=organization_id,
            policy_key=policy_key,
            name=name,
            description=description,
            effect=effect,
            conditions=conditions,
            created_by_user_id=user_id,
        )
        self._audit_logs.record(
            event_type="workflow_policy_draft_created",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"policy_key": policy_key, "version": policy.version},
        )
        self._db.commit()
        return policy

    def get_owned(
        self, workflow_policy_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> WorkflowPolicy:
        policy = self._policies.get_owned(workflow_policy_id, organization_id=organization_id)
        if policy is None:
            raise NotFoundError("Workflow policy not found.")
        return policy

    def list_for_organization(self, organization_id: uuid.UUID) -> list[WorkflowPolicy]:
        return self._policies.list_for_organization(organization_id)

    def list_versions(
        self, *, organization_id: uuid.UUID, policy_key: str
    ) -> list[WorkflowPolicy]:
        return self._policies.list_versions(organization_id=organization_id, policy_key=policy_key)

    def publish(
        self, workflow_policy_id: uuid.UUID, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkflowPolicy:
        policy = self.get_owned(workflow_policy_id, organization_id=organization_id)
        self._policies.publish(policy)
        self._audit_logs.record(
            event_type="workflow_policy_published",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"policy_key": policy.policy_key, "version": policy.version},
        )
        self._db.commit()
        return policy

    def archive(
        self, workflow_policy_id: uuid.UUID, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkflowPolicy:
        policy = self.get_owned(workflow_policy_id, organization_id=organization_id)
        self._policies.archive(policy)
        self._audit_logs.record(
            event_type="workflow_policy_archived",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"policy_key": policy.policy_key, "version": policy.version},
        )
        self._db.commit()
        return policy
