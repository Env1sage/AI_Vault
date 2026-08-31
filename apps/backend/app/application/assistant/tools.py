import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.application.search_service import SearchService
from app.application.storage_intelligence_service import StorageIntelligenceService
from vault_shared import NotFoundError, get_settings
from vault_shared.ai_gateway import AIGateway
from vault_shared.db.repositories import (
    DuplicateGroupRepository,
    FileIntelligenceRepository,
    FileRepository,
)
from vault_shared.formatting import human_bytes
from vault_shared.storage_intelligence.thresholds import (
    INACTIVE_FILE_DAYS_DEFAULT,
    LARGE_FILE_BYTES_DEFAULT,
    OLD_FILE_DAYS_DEFAULT,
)


@dataclass(frozen=True)
class ToolContext:
    """Everything a tool handler needs, with identity fields resolved
    server-side (from `get_current_user`, upstream in `ConversationService.
    ask()`) rather than accepted from the LLM. Handlers must never read an
    `organization_id`/`user_id` out of their `args` dict — the security
    boundary is this dataclass's shape, not a convention a handler could
    forget to follow."""

    db: Session
    organization_id: uuid.UUID
    user_id: uuid.UUID
    ai_gateway: AIGateway


def _clamp_int(raw: Any, *, default: int, minimum: int, maximum: int) -> int:
    """Missing/non-numeric/negative → default. Above the ceiling → the
    ceiling, never the raw LLM-supplied value — every numeric tool
    argument passes through this, so no handler can be pointed at an
    unbounded page size or a nonsensical threshold."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    if value < minimum:
        return default
    return min(value, maximum)


def _bytes_pair(prefix: str, num_bytes: int | None) -> dict[str, Any]:
    value = num_bytes or 0
    return {f"{prefix}_bytes": value, f"{prefix}_human": human_bytes(value)}


def _clamp_limit(args: dict[str, Any], *, default: int = 10) -> int:
    settings = get_settings()
    return _clamp_int(
        args.get("limit"), default=default, minimum=1, maximum=settings.ai_max_context_items
    )


def get_storage_overview(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    service = StorageIntelligenceService(ctx.db)
    snapshot = service.get_latest_snapshot(ctx.organization_id)
    job = service.get_latest_job(ctx.organization_id)

    result: dict[str, Any] = {
        "available": snapshot is not None,
        "as_of": snapshot.created_at.isoformat() if snapshot else None,
        "analysis_status": job.status if job else None,
        "analysis_error": job.error if job else None,
    }
    if snapshot is None:
        return result

    result.update(
        {
            "total_files": snapshot.total_files,
            "total_folders": snapshot.total_folders,
            "duplicate_group_count": snapshot.duplicate_group_count,
            "duplicate_file_count": snapshot.duplicate_file_count,
            "large_file_count": snapshot.large_file_count,
            "old_file_count": snapshot.old_file_count,
            "inactive_file_count": snapshot.inactive_file_count,
            "temporary_candidate_count": snapshot.temporary_candidate_count,
            **_bytes_pair("total_size", snapshot.total_size_bytes),
            **_bytes_pair("total_potential_savings", snapshot.total_potential_savings_bytes),
            **_bytes_pair("duplicate_recoverable", snapshot.duplicate_recoverable_bytes),
        }
    )
    return result


def get_storage_statistics(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    service = StorageIntelligenceService(ctx.db)
    snapshot = service.get_latest_snapshot(ctx.organization_id)
    if snapshot is None:
        return {
            "available": False,
            "as_of": None,
            "by_type": [],
            "by_size_bucket": [],
            "by_source": [],
        }

    total = snapshot.total_size_bytes or 0

    def _percent(num_bytes: int) -> float:
        return round(num_bytes / total * 100, 1) if total else 0.0

    def _simple_rows(breakdown: dict[str, int]) -> list[dict[str, Any]]:
        items = sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True)
        return [
            {
                "category": key,
                "bytes": value,
                "human": human_bytes(value),
                "percent": _percent(value),
            }
            for key, value in items[: settings.ai_max_context_items]
        ]

    source_items = sorted(
        snapshot.breakdown_by_source_bytes.items(),
        key=lambda kv: kv[1].get("bytes", 0),
        reverse=True,
    )
    by_source = [
        {
            "name": value.get("name", key),
            "bytes": value.get("bytes", 0),
            "human": human_bytes(value.get("bytes", 0)),
            "percent": _percent(value.get("bytes", 0)),
        }
        for key, value in source_items[: settings.ai_max_context_items]
    ]

    return {
        "available": True,
        "as_of": snapshot.created_at.isoformat(),
        "by_type": _simple_rows(snapshot.breakdown_by_type_bytes),
        "by_size_bucket": _simple_rows(snapshot.breakdown_by_size_bucket_bytes),
        "by_source": by_source,
    }


def get_duplicate_summary(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    service = StorageIntelligenceService(ctx.db)
    duplicate_groups_repo = DuplicateGroupRepository(ctx.db)
    limit = _clamp_int(
        args.get("limit"), default=5, minimum=1, maximum=settings.ai_max_context_items
    )
    groups, total = service.list_duplicate_groups(ctx.organization_id, limit=limit, offset=0)

    group_rows = []
    for group in groups:
        members = duplicate_groups_repo.list_members_with_files(group.id)
        keep_name = next(
            (file.name for member, file in members if member.is_recommended_keep), None
        )
        sample_names = [file.name for _member, file in members[:3]]
        group_rows.append(
            {
                "group_id": str(group.id),
                "checksum_prefix": group.checksum[:8],
                "file_count": group.file_count,
                "recommended_keep_file_id": (
                    str(group.recommended_keep_file_id) if group.recommended_keep_file_id else None
                ),
                "recommended_keep_name": keep_name,
                "recommended_keep_reason": group.recommended_keep_reason,
                "recommended_keep_confidence": group.recommended_keep_confidence,
                "sample_file_names": sample_names,
                **_bytes_pair("total_size", group.total_size_bytes),
                **_bytes_pair("recoverable_size", group.recoverable_size_bytes),
            }
        )

    return {"total_groups": total, "returned": len(group_rows), "groups": group_rows}


def get_duplicate_group(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    raw_id = args.get("group_id")
    try:
        group_id = uuid.UUID(str(raw_id))
    except (TypeError, ValueError):
        return {"error": "No valid duplicate group id was given."}

    service = StorageIntelligenceService(ctx.db)
    try:
        group, members = service.get_duplicate_group(group_id, organization_id=ctx.organization_id)
    except NotFoundError:
        return {"error": "That duplicate group could not be found."}

    member_rows = [
        {
            "file_id": str(file.id),
            "name": file.name,
            "path": file.path,
            "owner_email": file.owner_email,
            "modified_at": file.provider_modified_at.isoformat()
            if file.provider_modified_at
            else None,
            "is_recommended_keep": is_keep,
            **_bytes_pair("size", file.size_bytes),
        }
        for file, is_keep in members[: settings.ai_max_context_items]
    ]

    return {
        "group_id": str(group.id),
        "checksum": group.checksum,
        "file_count": group.file_count,
        "recommended_keep_reason": group.recommended_keep_reason,
        "recommended_keep_confidence": group.recommended_keep_confidence,
        "members": member_rows,
        **_bytes_pair("total_size", group.total_size_bytes),
        **_bytes_pair("recoverable_size", group.recoverable_size_bytes),
    }


def _file_row(file: Any, *, include_last_viewed: bool = False) -> dict[str, Any]:
    row = {
        "file_id": str(file.id),
        "name": file.name,
        "path": file.path,
        "mime_type": file.mime_type,
        "modified_at": file.provider_modified_at.isoformat() if file.provider_modified_at else None,
        **_bytes_pair("size", file.size_bytes),
    }
    if include_last_viewed:
        row["last_viewed_at"] = (
            file.provider_viewed_at.isoformat() if file.provider_viewed_at else None
        )
    return row


def get_large_files(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    service = StorageIntelligenceService(ctx.db)
    limit = _clamp_limit(args)
    min_size_bytes = _clamp_int(
        args.get("min_size_bytes"),
        default=LARGE_FILE_BYTES_DEFAULT,
        minimum=0,
        maximum=settings.ai_max_large_file_threshold_bytes,
    )
    files, total = service.list_large_files(
        ctx.organization_id, min_size_bytes=min_size_bytes, limit=limit, offset=0
    )
    return {
        "total": total,
        "returned": len(files),
        "threshold": {
            "kind": "min_size_bytes",
            "value": min_size_bytes,
            "human": human_bytes(min_size_bytes),
        },
        "files": [_file_row(f) for f in files],
    }


def get_old_files(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    service = StorageIntelligenceService(ctx.db)
    limit = _clamp_limit(args)
    older_than_days = _clamp_int(
        args.get("older_than_days"),
        default=OLD_FILE_DAYS_DEFAULT,
        minimum=1,
        maximum=settings.ai_max_age_days,
    )
    files, total = service.list_old_files(
        ctx.organization_id, older_than_days=older_than_days, limit=limit, offset=0
    )
    return {
        "total": total,
        "returned": len(files),
        "threshold": {
            "kind": "older_than_days",
            "value": older_than_days,
            "human": f"{older_than_days} days",
        },
        "files": [_file_row(f) for f in files],
    }


def get_inactive_files(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    service = StorageIntelligenceService(ctx.db)
    limit = _clamp_limit(args)
    inactive_days = _clamp_int(
        args.get("inactive_days"),
        default=INACTIVE_FILE_DAYS_DEFAULT,
        minimum=1,
        maximum=settings.ai_max_age_days,
    )
    files, total = service.list_inactive_files(
        ctx.organization_id, inactive_days=inactive_days, limit=limit, offset=0
    )
    return {
        "total": total,
        "returned": len(files),
        "threshold": {
            "kind": "inactive_days",
            "value": inactive_days,
            "human": f"{inactive_days} days",
        },
        "files": [_file_row(f, include_last_viewed=True) for f in files],
    }


def get_cleanup_candidates(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    service = StorageIntelligenceService(ctx.db)
    limit = _clamp_limit(args)
    files, total = service.list_candidates(ctx.organization_id, limit=limit, offset=0)
    return {
        "total": total,
        "returned": len(files),
        "note": "These are candidates identified by name/type heuristics for manual review — "
        "not a deletion recommendation.",
        "files": [_file_row(f) for f in files],
    }


def search_files(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    query_text = str(args.get("query") or "").strip()
    if not query_text:
        return {"returned": 0, "files": []}

    limit = _clamp_int(
        args.get("limit"), default=10, minimum=1, maximum=settings.ai_max_search_results
    )
    search = SearchService(ctx.db, ai_gateway=ctx.ai_gateway)
    results = search.search(
        query_text, organization_id=ctx.organization_id, user_id=ctx.user_id, limit=limit
    )
    return {
        "returned": len(results),
        "files": [
            {
                **_file_row(result.file),
                "score": result.score,
                "retrieval_method": result.retrieval_method,
            }
            for result in results
        ],
    }


def get_file(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    raw_id = args.get("file_id")
    try:
        file_id = uuid.UUID(str(raw_id))
    except (TypeError, ValueError):
        return {"found": False}

    file = FileRepository(ctx.db).get_owned_by_organization(
        file_id, organization_id=ctx.organization_id
    )
    if file is None:
        return {"found": False}

    intelligence = FileIntelligenceRepository(ctx.db).get_by_file_id(file.id)
    return {
        "found": True,
        "file_id": str(file.id),
        "name": file.name,
        "path": file.path,
        "mime_type": file.mime_type,
        "is_shared": file.is_shared,
        "owner_email": file.owner_email,
        "created_at": file.provider_created_at.isoformat() if file.provider_created_at else None,
        "modified_at": file.provider_modified_at.isoformat() if file.provider_modified_at else None,
        "last_viewed_at": file.provider_viewed_at.isoformat() if file.provider_viewed_at else None,
        "checksum": file.checksum,
        "web_view_link": file.web_view_link,
        "summary": intelligence.summary if intelligence else None,
        "document_type": intelligence.document_type if intelligence else None,
        **_bytes_pair("size", file.size_bytes),
    }
