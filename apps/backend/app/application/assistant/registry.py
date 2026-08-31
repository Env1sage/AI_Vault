from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.application.assistant.tools import (
    ToolContext,
    get_cleanup_candidates,
    get_duplicate_group,
    get_duplicate_summary,
    get_file,
    get_inactive_files,
    get_large_files,
    get_old_files,
    get_storage_overview,
    get_storage_statistics,
    search_files,
)
from vault_shared import get_settings


@dataclass(frozen=True)
class ArgSpec:
    """Descriptive metadata only in V1 — the registry doesn't itself
    enforce these bounds (each handler in `tools.py` clamps its own args
    via `_clamp_int`, independently). This is the shape a future
    model-driven function-calling dispatcher would serialize as a JSON
    schema; keeping it here now means that upgrade is additive, not a
    rewrite."""

    kind: str
    description: str
    default: Any = None
    minimum: Any = None
    maximum: Any = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    handler: Callable[[ToolContext, dict[str, Any]], dict[str, Any]]
    arg_schema: dict[str, ArgSpec] = field(default_factory=dict)
    cacheable: bool = False
    cite_files: bool = False
    description: str = ""


def _build_registry() -> dict[str, ToolSpec]:
    settings = get_settings()
    specs = [
        ToolSpec(
            name="get_storage_overview",
            handler=get_storage_overview,
            cacheable=True,
            description="Headline storage statistics: total size, file count, duplicates, "
            "large/old/inactive/candidate counts.",
        ),
        ToolSpec(
            name="get_storage_statistics",
            handler=get_storage_statistics,
            cacheable=True,
            description="Storage breakdown by file type, size bucket, and connected source.",
        ),
        ToolSpec(
            name="get_duplicate_summary",
            handler=get_duplicate_summary,
            arg_schema={
                "limit": ArgSpec(
                    "int", "How many duplicate groups to return.",
                    default=5, minimum=1, maximum=settings.ai_max_context_items,
                )
            },
            cacheable=True,
            cite_files=False,
            description="Summary of duplicate-file groups: counts, recoverable space, top groups.",
        ),
        ToolSpec(
            name="get_duplicate_group",
            handler=get_duplicate_group,
            arg_schema={"group_id": ArgSpec("uuid", "The duplicate group's id.")},
            cite_files=True,
            description="Full detail for one specific duplicate group, including every member "
            "file.",
        ),
        ToolSpec(
            name="get_large_files",
            handler=get_large_files,
            arg_schema={
                "min_size_bytes": ArgSpec(
                    "int", "Minimum file size in bytes.",
                    default=None, minimum=0, maximum=settings.ai_max_large_file_threshold_bytes,
                ),
                "limit": ArgSpec(
                    "int", "How many files to return.",
                    default=10, minimum=1, maximum=settings.ai_max_context_items,
                ),
            },
            cite_files=True,
            description="The organization's largest files.",
        ),
        ToolSpec(
            name="get_old_files",
            handler=get_old_files,
            arg_schema={
                "older_than_days": ArgSpec(
                    "int", "Minimum age in days since last modification.",
                    default=None, minimum=1, maximum=settings.ai_max_age_days,
                ),
                "limit": ArgSpec(
                    "int", "How many files to return.",
                    default=10, minimum=1, maximum=settings.ai_max_context_items,
                ),
            },
            cite_files=True,
            description="Files not modified in a long time.",
        ),
        ToolSpec(
            name="get_inactive_files",
            handler=get_inactive_files,
            arg_schema={
                "inactive_days": ArgSpec(
                    "int", "Minimum days since the file was last opened.",
                    default=None, minimum=1, maximum=settings.ai_max_age_days,
                ),
                "limit": ArgSpec(
                    "int", "How many files to return.",
                    default=10, minimum=1, maximum=settings.ai_max_context_items,
                ),
            },
            cite_files=True,
            description="Files nobody has opened in a long time.",
        ),
        ToolSpec(
            name="get_cleanup_candidates",
            handler=get_cleanup_candidates,
            arg_schema={
                "limit": ArgSpec(
                    "int", "How many candidates to return.",
                    default=10, minimum=1, maximum=settings.ai_max_context_items,
                )
            },
            cite_files=True,
            cacheable=True,
            description="Files that look like temporary/scratch files by name pattern — "
            "candidates for manual review, never a deletion recommendation.",
        ),
        ToolSpec(
            name="search_files",
            handler=search_files,
            arg_schema={
                "query": ArgSpec("str", "The search text."),
                "limit": ArgSpec(
                    "int", "How many results to return.",
                    default=10, minimum=1, maximum=settings.ai_max_search_results,
                ),
            },
            cite_files=True,
            description="Natural-language file search over names and content.",
        ),
        ToolSpec(
            name="get_file",
            handler=get_file,
            arg_schema={"file_id": ArgSpec("uuid", "The file's id.")},
            cite_files=True,
            description="Full detail for one specific file.",
        ),
    ]
    return {spec.name: spec for spec in specs}


TOOL_REGISTRY: dict[str, ToolSpec] = _build_registry()
