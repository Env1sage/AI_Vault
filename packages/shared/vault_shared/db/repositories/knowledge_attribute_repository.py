import uuid

from sqlalchemy.orm import Session

from vault_shared.db.models import KnowledgeAttribute


class KnowledgeAttributeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_file(self, file_id: uuid.UUID) -> list[KnowledgeAttribute]:
        return self._session.query(KnowledgeAttribute).filter_by(file_id=file_id).all()

    def list_department_values_for_files(self, file_ids: list[uuid.UUID]) -> list[str]:
        """Used by the Recommendation Engine to populate `Recommendation.
        related_departments` — the sorted, deduplicated `department`
        knowledge attribute values across a bounded set of affected files
        (never the whole organization), so a recommendation can say which
        departments it touches without a per-recommendation full scan."""
        if not file_ids:
            return []
        rows = (
            self._session.query(KnowledgeAttribute.value)
            .filter(
                KnowledgeAttribute.file_id.in_(file_ids),
                KnowledgeAttribute.attribute_type == "department",
            )
            .distinct()
            .all()
        )
        return sorted({value for (value,) in rows})

    def replace_for_file(
        self, file_id: uuid.UUID, attributes: list[dict]
    ) -> list[KnowledgeAttribute]:
        """Deletes every existing attribute for this file and inserts the
        freshly-inferred set — a reprocess can legitimately change which
        department/time-period a file resolves to, and the unique
        constraint on (file_id, attribute_type, value) would otherwise leave
        a superseded value stranded forever rather than replacing it."""
        self._session.query(KnowledgeAttribute).filter_by(file_id=file_id).delete()
        created = [
            KnowledgeAttribute(
                file_id=file_id,
                attribute_type=attr["attribute_type"],
                value=attr["value"],
                confidence=attr["confidence"],
                source=attr["source"],
            )
            for attr in attributes
        ]
        self._session.add_all(created)
        self._session.flush()
        return created
