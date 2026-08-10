import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vault_shared.db.models import WorkflowVersion, WorkflowVersionStatus


class WorkflowVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, *, workflow_id: uuid.UUID, version_number: int, created_by_user_id: uuid.UUID
    ) -> WorkflowVersion:
        version = WorkflowVersion(
            workflow_id=workflow_id,
            version_number=version_number,
            created_by_user_id=created_by_user_id,
        )
        self._session.add(version)
        self._session.flush()
        return version

    def get_by_id(self, workflow_version_id: uuid.UUID) -> WorkflowVersion | None:
        return self._session.get(WorkflowVersion, workflow_version_id)

    def get_owned(
        self, workflow_version_id: uuid.UUID, *, workflow_id: uuid.UUID
    ) -> WorkflowVersion | None:
        return (
            self._session.query(WorkflowVersion)
            .filter_by(id=workflow_version_id, workflow_id=workflow_id)
            .first()
        )

    def get_published(self, workflow_id: uuid.UUID) -> WorkflowVersion | None:
        return (
            self._session.query(WorkflowVersion)
            .filter_by(workflow_id=workflow_id, status=WorkflowVersionStatus.PUBLISHED)
            .first()
        )

    def list_for_workflow(self, workflow_id: uuid.UUID) -> list[WorkflowVersion]:
        return (
            self._session.query(WorkflowVersion)
            .filter_by(workflow_id=workflow_id)
            .order_by(WorkflowVersion.version_number.desc())
            .all()
        )

    def next_version_number(self, workflow_id: uuid.UUID) -> int:
        latest = (
            self._session.query(WorkflowVersion)
            .filter_by(workflow_id=workflow_id)
            .order_by(WorkflowVersion.version_number.desc())
            .first()
        )
        return (latest.version_number + 1) if latest else 1

    def publish(self, version: WorkflowVersion) -> None:
        """Publishing one version always supersedes whatever was previously
        published for the same workflow — enforces "at most one PUBLISHED
        version per workflow" without a DB constraint (same pattern as
        `Recommendation`'s natural-key upsert). Publishing an older
        `SUPERSEDED` version again is exactly how "rollback" works."""
        currently_published = self.get_published(version.workflow_id)
        if currently_published is not None and currently_published.id != version.id:
            currently_published.status = WorkflowVersionStatus.SUPERSEDED
        version.status = WorkflowVersionStatus.PUBLISHED
        version.published_at = datetime.now(UTC)
        self._session.flush()
