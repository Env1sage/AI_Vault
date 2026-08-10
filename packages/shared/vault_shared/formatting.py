def human_bytes(num_bytes: float) -> str:
    """A plain, dependency-free byte formatter — the Recommendation
    Engine's estimated-impact prose (Phase 7) and the Execution Planner's
    estimated-impact prose (Phase 8) both need "~2.1 GB", not a raw
    integer (Phase 7 spec's own example: "reduce storage usage by
    approximately 120 GB"). Lives in `packages/shared` (not either app's
    own package) specifically because both `apps/worker`'s Recommendation
    Engine and `apps/backend`'s Execution Planner need it."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024.0 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"
