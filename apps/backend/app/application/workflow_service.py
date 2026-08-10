import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from vault_shared import ConflictError, NotFoundError, ValidationError
from vault_shared.db.models import (
    Workflow,
    WorkflowNode,
    WorkflowNodeType,
    WorkflowStatus,
    WorkflowVersion,
    WorkflowVersionStatus,
)
from vault_shared.db.repositories import (
    AuditLogRepository,
    WorkflowExecutionRepository,
    WorkflowNodeRepository,
    WorkflowRepository,
    WorkflowVersionRepository,
)

_VALID_NODE_TYPES = {member.value for member in WorkflowNodeType}
_VALID_WORKFLOW_STATUSES = {member.value for member in WorkflowStatus}


@dataclass(frozen=True)
class WorkflowDetail:
    workflow: Workflow
    published_version: WorkflowVersion | None
    draft_version: WorkflowVersion | None


class WorkflowService:
    """The Workflow orchestration surface (Phase 9 spec's Workflow Builder
    + Workflow Version Management) — CRUD, node-graph editing, publish/
    rollback, pause/resume/disable/clone. Never executes a node itself
    (that's `worker.workflow.execution_service.WorkflowExecutionService`);
    this class only ever reads/writes the graph's definition and lifecycle
    state. See ADR-021."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._workflows = WorkflowRepository(db)
        self._versions = WorkflowVersionRepository(db)
        self._nodes = WorkflowNodeRepository(db)
        self._executions = WorkflowExecutionRepository(db)
        self._audit_logs = AuditLogRepository(db)

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> Workflow:
        workflow = self._workflows.create(
            organization_id=organization_id,
            created_by_user_id=user_id,
            name=name,
            description=description,
        )
        self._versions.create(
            workflow_id=workflow.id, version_number=1, created_by_user_id=user_id
        )
        self._audit_logs.record(
            event_type="workflow_created",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"workflow_id": str(workflow.id)},
        )
        self._db.commit()
        return workflow

    def get_owned(self, workflow_id: uuid.UUID, *, organization_id: uuid.UUID) -> Workflow:
        workflow = self._workflows.get_owned(workflow_id, organization_id=organization_id)
        if workflow is None:
            raise NotFoundError("Workflow not found.")
        return workflow

    def get_detail(self, workflow_id: uuid.UUID, *, organization_id: uuid.UUID) -> WorkflowDetail:
        workflow = self.get_owned(workflow_id, organization_id=organization_id)
        published = self._versions.get_published(workflow_id)
        versions = self._versions.list_for_workflow(workflow_id)
        draft = next((v for v in versions if v.status == WorkflowVersionStatus.DRAFT), None)
        return WorkflowDetail(workflow=workflow, published_version=published, draft_version=draft)

    def list_for_organization(
        self, organization_id: uuid.UUID, *, status: str | None = None
    ) -> list[Workflow]:
        return self._workflows.list_for_organization(organization_id, status=status)

    def list_versions(
        self, workflow_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> list[WorkflowVersion]:
        self.get_owned(workflow_id, organization_id=organization_id)
        return self._versions.list_for_workflow(workflow_id)

    def get_or_create_draft(
        self, workflow_id: uuid.UUID, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> tuple[WorkflowVersion, list[WorkflowNode]]:
        """The version a founder is currently editing. If the latest
        version is already published, a fresh draft is created — pre-
        populated with a copy of the published version's nodes, so editing
        an already-live workflow doesn't start from a blank graph."""
        workflow = self.get_owned(workflow_id, organization_id=organization_id)
        versions = self._versions.list_for_workflow(workflow_id)
        latest = versions[0] if versions else None

        if latest is not None and latest.status == WorkflowVersionStatus.DRAFT:
            return latest, self._nodes.list_for_version(latest.id)

        new_version = self._versions.create(
            workflow_id=workflow.id,
            version_number=self._versions.next_version_number(workflow.id),
            created_by_user_id=user_id,
        )
        source_nodes = self._nodes.list_for_version(latest.id) if latest else []
        cloned_nodes = self._clone_nodes(source_nodes, into_version_id=new_version.id)
        self._db.commit()
        return new_version, cloned_nodes

    def replace_nodes(
        self,
        workflow_version_id: uuid.UUID,
        *,
        workflow_id: uuid.UUID,
        organization_id: uuid.UUID,
        nodes: list[dict],
    ) -> list[WorkflowNode]:
        """Replaces a draft version's entire node graph in one call — the
        Workflow Builder submits the whole graph, not incremental per-node
        edits (a JSON/form-based builder this phase, not a live drag-and-
        drop canvas — the phase spec explicitly says the backend must not
        depend on one). `nodes` use a client-assigned string `key` for
        cross-referencing in `next_nodes` (e.g. `{"default": "n2"}`) since
        real ids don't exist until after insert; this method translates
        keys to real ids in a second pass. Only a `DRAFT` version's nodes
        can be replaced — a published version is frozen once an execution
        may have referenced it."""
        self.get_owned(workflow_id, organization_id=organization_id)
        version = self._versions.get_owned(workflow_version_id, workflow_id=workflow_id)
        if version is None:
            raise NotFoundError("Workflow version not found.")
        if version.status != WorkflowVersionStatus.DRAFT:
            raise ConflictError("Only a draft version's nodes can be edited.")

        self._validate_graph(nodes)

        self._nodes.delete_for_version(version.id)
        key_to_id: dict[str, uuid.UUID] = {}
        created: list[WorkflowNode] = []
        for node_input in nodes:
            node = self._nodes.create(
                workflow_version_id=version.id,
                node_type=node_input["node_type"],
                name=node_input["name"],
                config=node_input.get("config") or {},
                next_nodes={},
                position_x=node_input.get("position_x", 0),
                position_y=node_input.get("position_y", 0),
            )
            key_to_id[node_input["key"]] = node.id
            created.append(node)

        for node, node_input in zip(created, nodes, strict=True):
            translated = {
                outcome: str(key_to_id[target_key])
                for outcome, target_key in (node_input.get("next_nodes") or {}).items()
            }
            self._nodes.update_next_nodes(node, next_nodes=translated)

        self._db.commit()
        return created

    def publish(
        self, workflow_id: uuid.UUID, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkflowVersion:
        workflow = self.get_owned(workflow_id, organization_id=organization_id)
        versions = self._versions.list_for_workflow(workflow_id)
        draft = next((v for v in versions if v.status == WorkflowVersionStatus.DRAFT), None)
        if draft is None:
            raise ConflictError("This workflow has no draft version to publish.")

        nodes = self._nodes.list_for_version(draft.id)
        if not nodes:
            raise ValidationError("Cannot publish a workflow with no nodes.")

        self._versions.publish(draft)
        self._audit_logs.record(
            event_type="workflow_published",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"workflow_id": str(workflow.id), "workflow_version_id": str(draft.id)},
        )
        self._db.commit()
        return draft

    def rollback_to_version(
        self,
        workflow_id: uuid.UUID,
        workflow_version_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> WorkflowVersion:
        """"Rollback" is republishing an older, already-`SUPERSEDED`
        version — no new version is created, no nodes are copied; the
        version's own history (and every past `WorkflowExecution` that ran
        it) is untouched."""
        self.get_owned(workflow_id, organization_id=organization_id)
        version = self._versions.get_owned(workflow_version_id, workflow_id=workflow_id)
        if version is None:
            raise NotFoundError("Workflow version not found.")
        if version.status == WorkflowVersionStatus.DRAFT:
            raise ConflictError("A draft version must be published, not rolled back to.")

        self._versions.publish(version)
        self._audit_logs.record(
            event_type="workflow_rolled_back",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"workflow_id": str(workflow_id), "workflow_version_id": str(version.id)},
        )
        self._db.commit()
        return version

    def set_status(
        self,
        workflow_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        status: str,
    ) -> Workflow:
        if status not in _VALID_WORKFLOW_STATUSES:
            raise ValidationError(f"Unknown workflow status: {status}")
        workflow = self.get_owned(workflow_id, organization_id=organization_id)
        self._workflows.update_status(workflow, status=status)
        self._audit_logs.record(
            event_type="workflow_status_changed",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"workflow_id": str(workflow_id), "status": status},
        )
        self._db.commit()
        return workflow

    def clone(
        self, workflow_id: uuid.UUID, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> Workflow:
        source = self.get_owned(workflow_id, organization_id=organization_id)
        cloned = self._workflows.create(
            organization_id=organization_id,
            created_by_user_id=user_id,
            name=f"{source.name} (copy)",
            description=source.description,
        )
        new_version = self._versions.create(
            workflow_id=cloned.id, version_number=1, created_by_user_id=user_id
        )
        source_version = self._versions.get_published(workflow_id) or (
            self._versions.list_for_workflow(workflow_id)[0]
            if self._versions.list_for_workflow(workflow_id)
            else None
        )
        if source_version is not None:
            self._clone_nodes(
                self._nodes.list_for_version(source_version.id), into_version_id=new_version.id
            )
        self._audit_logs.record(
            event_type="workflow_cloned",
            organization_id=organization_id,
            user_id=user_id,
            metadata={"source_workflow_id": str(workflow_id), "cloned_workflow_id": str(cloned.id)},
        )
        self._db.commit()
        return cloned

    def _clone_nodes(
        self, source_nodes: list[WorkflowNode], *, into_version_id: uuid.UUID
    ) -> list[WorkflowNode]:
        """Copies a node graph, remapping `next_nodes`' old node ids to the
        newly-created nodes' ids — same key-remapping shape as
        `replace_nodes`, just keyed by the source's real ids instead of
        client-submitted temporary ones."""
        old_to_new: dict[uuid.UUID, uuid.UUID] = {}
        created: list[WorkflowNode] = []
        for source in source_nodes:
            node = self._nodes.create(
                workflow_version_id=into_version_id,
                node_type=source.node_type,
                name=source.name,
                config=dict(source.config),
                next_nodes={},
                position_x=source.position_x,
                position_y=source.position_y,
            )
            old_to_new[source.id] = node.id
            created.append(node)

        for source, node in zip(source_nodes, created, strict=True):
            translated = {
                outcome: str(old_to_new[uuid.UUID(target)])
                for outcome, target in source.next_nodes.items()
                if uuid.UUID(target) in old_to_new
            }
            self._nodes.update_next_nodes(node, next_nodes=translated)
        return created

    @staticmethod
    def _validate_graph(nodes: list[dict]) -> None:
        if not nodes:
            raise ValidationError("A workflow needs at least one node.")
        keys = {node["key"] for node in nodes}
        if len(keys) != len(nodes):
            raise ValidationError("Node keys must be unique within a workflow version.")

        node_types = [node["node_type"] for node in nodes]
        for node_type in node_types:
            if node_type not in _VALID_NODE_TYPES:
                raise ValidationError(f"Unknown node type: {node_type}")
        if node_types.count(WorkflowNodeType.TRIGGER) != 1:
            raise ValidationError("A workflow must have exactly one trigger node.")
        if WorkflowNodeType.END not in node_types:
            raise ValidationError("A workflow must have at least one end node.")

        for node in nodes:
            for target_key in (node.get("next_nodes") or {}).values():
                if target_key not in keys:
                    raise ValidationError(
                        f"Node '{node['key']}' points to an unknown node '{target_key}'."
                    )
