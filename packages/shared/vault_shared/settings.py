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

    frontend_url: str = "http://localhost:5173"
    cors_allow_origins: str = "http://localhost:5173"

    # >=32 bytes so PyJWT doesn't warn about weak HMAC key length even with
    # the unset-in-env default — still just a placeholder, never use in prod.
    jwt_secret: str = "changeme-in-env-use-a-real-32-byte-secret"
    # Google Identity Services (client-side sign-in, Phase 2) verifies ID
    # tokens against this as the expected audience. The same client_id/secret
    # pair is also used for Phase 3's Workspace Connector — a separate,
    # server-side OAuth interaction (Drive access, not user identity) that
    # needs its own redirect URI/scopes/state handling, see ADR-014.
    google_client_id: str = ""
    google_client_secret: str = ""

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    refresh_cookie_name: str = "vault_refresh_token"
    # False for plain-http local dev; must be true anywhere served over HTTPS.
    cookie_secure: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
