from fastapi import APIRouter, Depends

from app.presentation.api.v1.schemas import UserProfileResponse
from app.presentation.dependencies.auth import get_current_user
from vault_shared.db.models import User

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/me", response_model=UserProfileResponse)
def get_my_profile(user: User = Depends(get_current_user)) -> UserProfileResponse:
    return UserProfileResponse.from_model(user)
