from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-sourced configuration shared by apps/backend and apps/worker.

    Every field documented here must have a matching entry in the repo-root
    `.env.example` (Engineering Handbook §13 — secrets never live in source,
    only placeholders documenting what's required).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "vault-service"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://vault:vault@localhost:5432/vault"
    redis_url: str = "redis://localhost:6379/0"

    # >=32 bytes so PyJWT doesn't warn about weak HMAC key length even with
    # the unset-in-env default — still just a placeholder, never use in prod.
    jwt_secret: str = "changeme-in-env-use-a-real-32-byte-secret"
    ai_gateway_key: str = ""
    # Google Identity Services (client-side sign-in, Phase 2) verifies ID
    # tokens against this as the expected audience. The same client_id/secret
    # pair is also used for Phase 3's Workspace Connector — a separate,
    # server-side OAuth interaction (Drive access, not user identity) that
    # needs its own redirect URI/scopes/state handling, see ADR-014.
    google_client_id: str = ""
    google_client_secret: str = ""

    frontend_url: str = "http://localhost:5173"
    cors_allow_origins: str = "http://localhost:5173"

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    refresh_cookie_name: str = "vault_refresh_token"
    # False for plain-http local dev; must be true anywhere served over HTTPS.
    cookie_secure: bool = False

    # Phase 3 — Google Workspace Connector (ADR-014). The redirect URI is a
    # *frontend* route: Google redirects the browser there, and that page
    # POSTs the code/state to the backend — the backend never receives a
    # browser-navigated redirect directly.
    google_workspace_redirect_uri: str = "http://localhost:5173/connectors/google/callback"
    # `drive.readonly` (Phases 3-7) is no longer sufficient once the
    # Execution Engine (Phase 8) can move/rename/trash a file — `drive.file`
    # was considered but only covers files the app itself created or the
    # user explicitly opened with it, not arbitrary pre-existing files a
    # recommendation might target, so this is the full `drive` scope
    # instead (Handbook §13's least-privilege rule: the narrowest scope
    # that satisfies the *current* phase's features — this is that scope
    # now that a write-capable phase exists, not a scope grabbed early).
    # A connector authorized before this phase only granted
    # `drive.readonly` (see `ConnectorCredentials.granted_scopes`) and must
    # be reconnected to pick up write access — see ADR-020.
    google_workspace_scopes: str = "openid email profile https://www.googleapis.com/auth/drive"
    oauth_state_ttl_seconds: int = 600
    # Fernet key (32 url-safe base64-encoded bytes) for encrypting OAuth
    # tokens at rest (Handbook §13 — "encrypt sensitive tokens before
    # persistence"). No safe default — generate with
    # `Fernet.generate_key()` and never reuse the .env.example placeholder
    # outside local development.
    connector_encryption_key: str = ""

    # Phase 8 — Execution Engine (ADR-020). `execution_max_retries`/
    # `execution_timeout_seconds` are read by the Celery task's retry
    # policy (worker.execution.run), the same shape as the scanner/
    # enrichment retry config; `approval_expiry_hours` is how long an
    # `ApprovalRequest` stays actionable before `ApprovalRequestRepository.
    # expire_if_overdue` marks it `EXPIRED`; `execution_rollback_enabled`
    # is a kill switch a founder can flip without a deploy if rollback
    # itself ever needs to be disabled.
    execution_max_retries: int = 3
    execution_timeout_seconds: int = 300
    approval_expiry_hours: int = 72
    execution_rollback_enabled: bool = True

    # Phase 9 — Automation Engine (ADR-021). `workflow_max_retries`/
    # `workflow_timeout_seconds` bound `worker.workflow.run`'s own retry/
    # wall-clock behavior, same shape as Phase 8's execution settings;
    # `scheduler_timezone` is the IANA zone cron expressions on `SCHEDULED`
    # triggers are interpreted in (e.g. "0 2 * * *" means 2am *here*, not
    # always UTC) — used by `croniter` in `WorkflowTriggerService`/
    # `SchedulerService`, independent of Celery's own broker timezone
    # (always UTC, unrelated); `notification_email_enabled` toggles the
    # email channel on/off without touching which provider backs it (the
    # founder's binding choice this phase: `StubEmailProvider`, never a
    # real send, regardless of this flag); `default_approval_timeout_hours`
    # is what a workflow's `APPROVAL` node uses for its `ApprovalRequest.
    # expires_at` when the node doesn't override it — same value as
    # `approval_expiry_hours` by default, kept as a separate setting since
    # the phase spec names both env vars independently.
    workflow_max_retries: int = 3
    workflow_timeout_seconds: int = 300
    scheduler_timezone: str = "UTC"
    notification_email_enabled: bool = False
    default_approval_timeout_hours: int = 72

    # Phase 10 — Production Hardening (ADR-022). `/v1/dashboard` is the
    # spec's own named example of an endpoint worth caching ("Dashboard
    # aggregation") — it's read by every page load of the Founder Command
    # Center but only actually changes once per scan/enrichment/embedding/
    # recommendation cycle, so a short TTL trades a few seconds of
    # staleness for skipping the DB entirely on repeat loads.
    dashboard_cache_ttl_seconds: int = 30

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
