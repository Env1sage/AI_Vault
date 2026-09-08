import uuid
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.application.file_service import FileService
from app.presentation.api.v1.schemas import (
    FileDetailResponse,
    FileListResponse,
    FileSummaryResponse,
    FolderSummaryResponse,
)
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_file_service
from vault_shared.db.models import User

files_router = APIRouter(tags=["files"])

_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 200


@files_router.get("/connectors/{connector_id}/files", response_model=FileListResponse)
def list_files(
    connector_id: uuid.UUID,
    limit: int = Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    ownership: Literal["mine", "shared"] | None = Query(default=None),
    user: User = Depends(get_current_user),
    service: FileService = Depends(get_file_service),
) -> FileListResponse:
    files, total = service.list_for_connector(
        connector_id,
        organization_id=user.organization_id,
        limit=limit,
        offset=offset,
        ownership=ownership,
    )
    return FileListResponse(items=[FileSummaryResponse.from_model(f) for f in files], total=total)


@files_router.get("/connectors/{connector_id}/folders", response_model=list[FolderSummaryResponse])
def search_folders(
    connector_id: uuid.UUID,
    query: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    service: FileService = Depends(get_file_service),
) -> list[FolderSummaryResponse]:
    folders = service.search_folders(
        connector_id, organization_id=user.organization_id, query=query, limit=limit
    )
    return [FolderSummaryResponse.from_model(f) for f in folders]


@files_router.get("/files/{file_id}", response_model=FileDetailResponse)
def get_file_detail(
    file_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: FileService = Depends(get_file_service),
) -> FileDetailResponse:
    detail = service.get_detail(file_id, organization_id=user.organization_id)
    return FileDetailResponse.from_detail(detail)


@files_router.get("/files/{file_id}/download")
def download_file(
    file_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: FileService = Depends(get_file_service),
) -> StreamingResponse:
    _file, stream, content_type, filename = service.get_download_stream(
        file_id, organization_id=user.organization_id
    )
    ascii_filename = filename.encode("ascii", "ignore").decode("ascii").strip() or "download"
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{quote(filename)}'
        )
    }
    return StreamingResponse(stream, media_type=content_type, headers=headers)
