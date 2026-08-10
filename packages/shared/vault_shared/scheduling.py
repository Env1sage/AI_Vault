from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from croniter import croniter

from vault_shared.settings import get_settings


def next_cron_run(cron: str, *, now: datetime | None = None) -> datetime:
    """The next occurrence of a `SCHEDULED` `WorkflowTrigger`'s cron
    expression, interpreted in `settings.scheduler_timezone` (Phase 9's
    `SCHEDULER_TIMEZONE` env var) — "0 2 * * *" means 2am in that zone,
    not always UTC. Returned as a timezone-aware UTC datetime (matching
    every other timestamp column in this codebase), converted from
    whatever zone the cron expression was evaluated in. Shared by
    `WorkflowTriggerService` (a trigger's first `next_run_at`) and
    `SchedulerService` (recomputing it after each fire) so both use
    identical timezone handling."""
    settings = get_settings()
    tz = ZoneInfo(settings.scheduler_timezone)
    reference = (now or datetime.now(tz)).astimezone(tz)
    next_run = croniter(cron, reference).get_next(datetime)
    return next_run.astimezone(UTC)
