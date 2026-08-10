from datetime import datetime

from pydantic import BaseModel, Field

from vault_shared.db.models import (
    Organization,
    StorageConnector,
    User,
)


class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None
    role: str
    organization_id: str
    created_at: datetime
    last_login_at: datetime | None

    @classmethod
    def from_model(cls, user: User) -> "UserProfileResponse":
        return cls(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            role=user.role.name,
            organization_id=str(user.organization_id),
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, organization: Organization) -> "OrganizationResponse":
        return cls(
            id=str(organization.id),
            name=organization.name,
            slug=organization.slug,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
        )


class OrganizationUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfileResponse


class ConnectorResponse(BaseModel):
    """Never includes token values — Phase 3 spec's "never expose refresh
    tokens" — those live only in ConnectorCredentials, which has no
    response schema of its own."""

    id: str
    provider: str
    status: str
    account_email: str | None
    workspace_domain: str | None
    last_verified_at: datetime | None
    last_failed_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, connector: StorageConnector) -> "ConnectorResponse":
        return cls(
            id=str(connector.id),
            provider=connector.provider,
            status=connector.status,
            account_email=connector.account_email,
            workspace_domain=connector.workspace_domain,
            last_verified_at=connector.last_verified_at,
            last_failed_at=connector.last_failed_at,
            last_error=connector.last_error,
            created_at=connector.created_at,
            updated_at=connector.updated_at,
        )


class InitiateConnectResponse(BaseModel):
    authorize_url: str


class CompleteConnectRequest(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


