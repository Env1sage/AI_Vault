from fastapi import APIRouter

from app.presentation.api.v1.auth import auth_router
from app.presentation.api.v1.connectors import connectors_router
from app.presentation.api.v1.conversations import conversations_router
from app.presentation.api.v1.dashboard import dashboard_router
from app.presentation.api.v1.embedding import embedding_router
from app.presentation.api.v1.enrichment import enrichment_router
from app.presentation.api.v1.files import files_router
from app.presentation.api.v1.organizations import organizations_router
from app.presentation.api.v1.recommendations import recommendations_router
from app.presentation.api.v1.scans import scans_router
from app.presentation.api.v1.search import search_router
from app.presentation.api.v1.users import users_router
from app.presentation.api.v1.version import version_router

v1_router = APIRouter()
v1_router.include_router(version_router)
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(organizations_router)
v1_router.include_router(connectors_router)
v1_router.include_router(scans_router)
v1_router.include_router(enrichment_router)
v1_router.include_router(files_router)
v1_router.include_router(embedding_router)
v1_router.include_router(search_router)
v1_router.include_router(conversations_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(recommendations_router)
