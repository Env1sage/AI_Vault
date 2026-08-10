from fastapi import APIRouter

from app.presentation.api.v1.auth import auth_router
from app.presentation.api.v1.organizations import organizations_router
from app.presentation.api.v1.users import users_router
from app.presentation.api.v1.version import version_router

v1_router = APIRouter()
v1_router.include_router(version_router)
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(organizations_router)
