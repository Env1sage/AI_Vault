from datetime import datetime

from pydantic import BaseModel, Field

from vault_shared.db.models import (
    Organization,
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


