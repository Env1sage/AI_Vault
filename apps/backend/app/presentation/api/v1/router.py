from fastapi import APIRouter

from app.presentation.api.v1.version import version_router

v1_router = APIRouter()
v1_router.include_router(version_router)
