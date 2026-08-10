import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import WorkflowNode


class WorkflowNodeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        workflow_version_id: uuid.UUID,
        node_type: str,
        name: str,
        config: dict,
        next_nodes: dict,
        position_x: int = 0,
        position_y: int = 0,
    ) -> WorkflowNode:
        node = WorkflowNode(
            workflow_version_id=workflow_version_id,
            node_type=node_type,
            name=name,
            config=config,
            next_nodes=next_nodes,
            position_x=position_x,
            position_y=position_y,
        )
        self._session.add(node)
        self._session.flush()
        return node

    def get_by_id(self, workflow_node_id: uuid.UUID) -> WorkflowNode | None:
        return self._session.get(WorkflowNode, workflow_node_id)

    def list_for_version(self, workflow_version_id: uuid.UUID) -> list[WorkflowNode]:
        return (
            self._session.query(WorkflowNode)
            .filter_by(workflow_version_id=workflow_version_id)
            .all()
        )

    def update_next_nodes(self, node: WorkflowNode, *, next_nodes: dict) -> None:
        """Second pass of graph creation: nodes are first inserted with
        `next_nodes={}` to obtain real ids, then updated once every node's
        client-submitted temporary key has been mapped to its real id — see
        `WorkflowService.replace_nodes`."""
        node.next_nodes = next_nodes
        self._session.flush()

    def delete_for_version(self, workflow_version_id: uuid.UUID) -> None:
        for node in self.list_for_version(workflow_version_id):
            self._session.delete(node)
        self._session.flush()
