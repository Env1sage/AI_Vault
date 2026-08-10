from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.infrastructure.cache.redis_client import get_redis
from vault_shared import get_logger
from vault_shared.db.session import get_engine

logger = get_logger("app.health")

health_router = APIRouter(tags=["health"])


@health_router.get("/health/live")
def liveness() -> dict:
    """Is this instance alive? No dependency checks — used by the orchestrator
    to decide whether to restart the process (Handbook §23)."""
    return {"status": "ok"}


@health_router.get("/health/ready")
def readiness(response: Response) -> dict:
    """Is this instance ready to serve traffic? Checks the dependencies every
    other endpoint needs: Postgres and Redis."""
    checks = {"database": False, "redis": False}

    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        logger.exception("readiness_check_failed", extra={"dependency": "database"})

    try:
        get_redis().ping()
        checks["redis"] = True
    except Exception:
        logger.exception("readiness_check_failed", extra={"dependency": "redis"})

    is_ready = all(checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {"status": "ok" if is_ready else "degraded", "checks": checks}
