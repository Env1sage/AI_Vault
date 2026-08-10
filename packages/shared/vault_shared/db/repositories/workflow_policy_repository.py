import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import WorkflowPolicy, WorkflowPolicyStatus


class WorkflowPolicyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_draft(
        self,
        *,
        organization_id: uuid.UUID,
        policy_key: str,
        name: str,
        description: str | None,
        effect: str,
        conditions: dict,
        created_by_user_id: uuid.UUID,
    ) -> WorkflowPolicy:
        """Every edit is a new row (full history retained, never an
        in-place update) — `version` increments from whatever the highest
        existing version for this `(organization_id, policy_key)` is."""
        version = self.next_version_number(organization_id=organization_id, policy_key=policy_key)
        policy = WorkflowPolicy(
            organization_id=organization_id,
            policy_key=policy_key,
            version=version,
            name=name,
            description=description,
            effect=effect,
            conditions=conditions,
            created_by_user_id=created_by_user_id,
        )
        self._session.add(policy)
        self._session.flush()
        return policy

    def next_version_number(self, *, organization_id: uuid.UUID, policy_key: str) -> int:
        latest = (
            self._session.query(WorkflowPolicy)
            .filter_by(organization_id=organization_id, policy_key=policy_key)
            .order_by(WorkflowPolicy.version.desc())
            .first()
        )
        return (latest.version + 1) if latest else 1

    def get_by_id(self, workflow_policy_id: uuid.UUID) -> WorkflowPolicy | None:
        return self._session.get(WorkflowPolicy, workflow_policy_id)

    def get_owned(
        self, workflow_policy_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> WorkflowPolicy | None:
        return (
            self._session.query(WorkflowPolicy)
            .filter_by(id=workflow_policy_id, organization_id=organization_id)
            .first()
        )

    def get_published(
        self, *, organization_id: uuid.UUID, policy_key: str
    ) -> WorkflowPolicy | None:
        return (
            self._session.query(WorkflowPolicy)
            .filter_by(
                organization_id=organization_id,
                policy_key=policy_key,
                status=WorkflowPolicyStatus.PUBLISHED,
            )
            .first()
        )

    def list_versions(
        self, *, organization_id: uuid.UUID, policy_key: str
    ) -> list[WorkflowPolicy]:
        return (
            self._session.query(WorkflowPolicy)
            .filter_by(organization_id=organization_id, policy_key=policy_key)
            .order_by(WorkflowPolicy.version.desc())
            .all()
        )

    def list_for_organization(self, organization_id: uuid.UUID) -> list[WorkflowPolicy]:
        """One row per distinct `policy_key` — the current published (or,
        if none published yet, most recent draft) version of each policy,
        for a policy-management list view."""
        rows = (
            self._session.query(WorkflowPolicy)
            .filter_by(organization_id=organization_id)
            .order_by(WorkflowPolicy.policy_key, WorkflowPolicy.version.desc())
            .all()
        )
        latest_by_key: dict[str, WorkflowPolicy] = {}
        for row in rows:
            if row.policy_key not in latest_by_key:
                latest_by_key[row.policy_key] = row
        return list(latest_by_key.values())

    def publish(self, policy: WorkflowPolicy) -> None:
        """Publishing this version archives whatever was previously
        published for the same `(organization_id, policy_key)` — at most
        one `PUBLISHED` row per key at a time (service-layer invariant)."""
        currently_published = self.get_published(
            organization_id=policy.organization_id, policy_key=policy.policy_key
        )
        if currently_published is not None and currently_published.id != policy.id:
            currently_published.status = WorkflowPolicyStatus.ARCHIVED
        policy.status = WorkflowPolicyStatus.PUBLISHED
        policy.published_at = datetime.now(UTC)
        self._session.flush()

    def archive(self, policy: WorkflowPolicy) -> None:
        policy.status = WorkflowPolicyStatus.ARCHIVED
        self._session.flush()
