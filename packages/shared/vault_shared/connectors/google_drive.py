from dataclasses import dataclass
from datetime import datetime

import requests

from vault_shared.errors import (
    DependencyUnavailableError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from vault_shared.logging import get_logger

logger = get_logger("vault_shared.connectors.google_drive")

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
_REQUEST_TIMEOUT_SECONDS = 30
_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
# Drive enforces no real limit on a file's `name` — some files (notably ones
# with no explicit title, where Drive falls back to a content excerpt) can
# return names far longer than any reasonable filename, which would
# otherwise overflow `folders.name`/`files.name` (String(1024)) and abort
# the whole ingest batch. Truncated here, at the connector boundary, so
# nothing downstream needs to know Drive can misbehave this way.
_MAX_NAME_LENGTH = 1024
_FILE_FIELDS = (
    "id,name,mimeType,parents,size,createdTime,modifiedTime,viewedByMeTime,"
    "owners(emailAddress),shared,md5Checksum,headRevisionId,trashed,webViewLink"
)


@dataclass(frozen=True)
class DriveFile:
    """Provider-shaped metadata, already parsed — the scanner service maps
    this onto the provider-neutral `Folder`/`File` DB models. Never carries
    file contents (Phase 4 spec: "do not download full file contents")."""

    id: str
    name: str
    mime_type: str
    parents: list[str]
    size: int | None
    created_time: datetime | None
    modified_time: datetime | None
    viewed_by_me_time: datetime | None
    owner_email: str | None
    shared: bool
    checksum: str | None
    version_id: str | None
    is_folder: bool
    trashed: bool
    web_view_link: str | None = None


@dataclass(frozen=True)
class DriveFilesPage:
    files: list[DriveFile]
    next_page_token: str | None


@dataclass(frozen=True)
class SharedDrive:
    id: str
    name: str


@dataclass(frozen=True)
class DriveChangesPage:
    changed_files: list[DriveFile]
    removed_file_ids: list[str]
    next_page_token: str | None
    new_start_page_token: str | None


class GoogleDriveClient:
    """The only module that calls Google Drive's Files/Drives/Changes API —
    mirrors the OAuth client's role for the token dance (Handbook §8.1's
    "leaf module" pattern). Always called with an access token already
    refreshed by `ConnectorTokenService`; this class has no knowledge of
    OAuth, encryption, or the database."""

    def list_shared_drives(self, *, access_token: str) -> list[SharedDrive]:
        drives: list[SharedDrive] = []
        page_token: str | None = None
        while True:
            params: dict[str, str | int] = {
                "pageSize": 100,
                "fields": "nextPageToken,drives(id,name)",
            }
            if page_token:
                params["pageToken"] = page_token
            payload = self._get(
                f"{DRIVE_API_BASE}/drives", access_token=access_token, params=params
            )
            drives.extend(
                SharedDrive(id=d["id"], name=d["name"]) for d in payload.get("drives", [])
            )
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
        return drives

    def list_files_page(
        self,
        *,
        access_token: str,
        drive_id: str | None,
        page_token: str | None,
        page_size: int = 1000,
    ) -> DriveFilesPage:
        params: dict[str, str | int] = {
            "pageSize": page_size,
            "fields": f"nextPageToken,files({_FILE_FIELDS})",
            "q": "trashed = false",
            "spaces": "drive",
            "includeItemsFromAllDrives": "true",
            "supportsAllDrives": "true",
            "corpora": "drive" if drive_id else "user",
        }
        if drive_id:
            params["driveId"] = drive_id
        if page_token:
            params["pageToken"] = page_token

        payload = self._get(f"{DRIVE_API_BASE}/files", access_token=access_token, params=params)
        files = [self._to_drive_file(item) for item in payload.get("files", [])]
        return DriveFilesPage(files=files, next_page_token=payload.get("nextPageToken"))

    def get_start_page_token(self, *, access_token: str, drive_id: str | None) -> str:
        params: dict[str, str] = {}
        if drive_id:
            params["driveId"] = drive_id
        payload = self._get(
            f"{DRIVE_API_BASE}/changes/startPageToken", access_token=access_token, params=params
        )
        return str(payload["startPageToken"])

    def list_changes_page(
        self, *, access_token: str, page_token: str, drive_id: str | None
    ) -> DriveChangesPage:
        params: dict[str, str] = {
            "pageToken": page_token,
            "fields": (
                f"nextPageToken,newStartPageToken,changes(fileId,removed,file({_FILE_FIELDS}))"
            ),
            "includeItemsFromAllDrives": "true",
            "supportsAllDrives": "true",
            "spaces": "drive",
        }
        if drive_id:
            params["driveId"] = drive_id
        payload = self._get(f"{DRIVE_API_BASE}/changes", access_token=access_token, params=params)

        changed: list[DriveFile] = []
        removed: list[str] = []
        for change in payload.get("changes", []):
            if change.get("removed"):
                removed.append(change["fileId"])
            elif change.get("file"):
                changed.append(self._to_drive_file(change["file"]))

        return DriveChangesPage(
            changed_files=changed,
            removed_file_ids=removed,
            next_page_token=payload.get("nextPageToken"),
            new_start_page_token=payload.get("newStartPageToken"),
        )

    def download_file(self, *, access_token: str, file_id: str) -> bytes:
        """Downloads raw bytes for a binary Drive file — used only by the
        Knowledge Engine's content extraction (Phase 5), never by the
        Scanner. Still strictly read-only against Drive; the caller decides
        whether a file is worth downloading at all (e.g. a size check
        against the already-scanned `File.size_bytes`) before calling this,
        since this client has no concept of an extraction size policy."""
        return self._get_bytes(
            f"{DRIVE_API_BASE}/files/{file_id}",
            access_token=access_token,
            params={"alt": "media"},
            content_access=True,
        )

    def export_file(self, *, access_token: str, file_id: str, export_mime_type: str) -> bytes:
        """Exports a native Google Workspace file (Docs/Sheets/Slides have no
        raw bytes of their own) to a requested MIME type — e.g. a Google Doc
        exported as `text/plain` for the extraction framework."""
        return self._get_bytes(
            f"{DRIVE_API_BASE}/files/{file_id}/export",
            access_token=access_token,
            params={"mimeType": export_mime_type},
            content_access=True,
        )

    def get_file(self, *, access_token: str, file_id: str) -> DriveFile:
        """A single-file live read — used by the Execution Engine (Phase 8)
        to re-check a file's current state (parent, name, trashed) right
        before mutating it, since the plan may have been created from a
        stale scan. Still read-only; the write methods below are the only
        ones that can mutate anything."""
        payload = self._get(
            f"{DRIVE_API_BASE}/files/{file_id}",
            access_token=access_token,
            params={"fields": _FILE_FIELDS, "supportsAllDrives": "true"},
        )
        return self._to_drive_file(payload)

    def move_file(
        self, *, access_token: str, file_id: str, add_parent_id: str, remove_parent_id: str
    ) -> DriveFile:
        """The Execution Engine's `move_file`/`move_folder` action (Phase 8)
        — Drive represents "move" as adding the new parent and removing the
        old one, not a single "set parent" call. Both parent ids are
        required (not inferred) so the caller — which already captured the
        file's pre-move state for `RollbackRecord` — is the single source
        of truth for what "moving back" means, not a second live read."""
        payload = self._patch(
            f"{DRIVE_API_BASE}/files/{file_id}",
            access_token=access_token,
            params={
                "addParents": add_parent_id,
                "removeParents": remove_parent_id,
                "fields": _FILE_FIELDS,
                "supportsAllDrives": "true",
            },
            json_body={},
        )
        return self._to_drive_file(payload)

    def rename_file(self, *, access_token: str, file_id: str, new_name: str) -> DriveFile:
        """The Execution Engine's `rename` action. Rollback is the same
        call with the pre-rename name captured in `RollbackRecord`."""
        payload = self._patch(
            f"{DRIVE_API_BASE}/files/{file_id}",
            access_token=access_token,
            params={"fields": _FILE_FIELDS, "supportsAllDrives": "true"},
            json_body={"name": new_name[:_MAX_NAME_LENGTH]},
        )
        return self._to_drive_file(payload)

    def set_trashed(self, *, access_token: str, file_id: str, trashed: bool) -> DriveFile:
        """The Execution Engine's `archive`/`remove_duplicate` actions
        (Phase 8) — implemented as Drive's own Trash (`trashed: true`),
        deliberately *not* permanent deletion (`files.delete`), which the
        phase spec explicitly forbids this phase. Trashed items remain
        recoverable directly in Drive and via `trashed: false` here, which
        is exactly what makes both actions genuinely reversible rather than
        "irreversible unless the founder digs through Drive's own trash
        UI in time.\""""
        payload = self._patch(
            f"{DRIVE_API_BASE}/files/{file_id}",
            access_token=access_token,
            params={"fields": _FILE_FIELDS, "supportsAllDrives": "true"},
            json_body={"trashed": trashed},
        )
        return self._to_drive_file(payload)

    def update_app_properties(
        self, *, access_token: str, file_id: str, properties: dict[str, str]
    ) -> DriveFile:
        """The Execution Engine's `update_metadata` action — Drive's
        `appProperties` are private key-value pairs visible only to the
        app that set them (not shown in Drive's own UI), the "where
        supported" metadata surface Phase 8's spec anticipates without
        needing write access to Drive's own description/properties field
        that other apps or the file owner might also rely on."""
        payload = self._patch(
            f"{DRIVE_API_BASE}/files/{file_id}",
            access_token=access_token,
            params={"fields": _FILE_FIELDS, "supportsAllDrives": "true"},
            json_body={"appProperties": properties},
        )
        return self._to_drive_file(payload)

    def _get(self, url: str, *, access_token: str, params: dict) -> dict:
        response = self._request(url, access_token=access_token, params=params)
        return response.json()

    def _patch(
        self, url: str, *, access_token: str, params: dict, json_body: dict
    ) -> dict:
        response = self._request(
            url, access_token=access_token, params=params, method="PATCH", json_body=json_body
        )
        return response.json()

    def _get_bytes(
        self, url: str, *, access_token: str, params: dict, content_access: bool = False
    ) -> bytes:
        response = self._request(
            url, access_token=access_token, params=params, content_access=content_access
        )
        return response.content

    def _request(
        self,
        url: str,
        *,
        access_token: str,
        params: dict,
        content_access: bool = False,
        method: str = "GET",
        json_body: dict | None = None,
    ) -> requests.Response:
        try:
            response = requests.request(
                method,
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
                json=json_body,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise DependencyUnavailableError("Could not reach Google Drive.") from exc

        if response.status_code == 401:
            raise UnauthorizedError("Google Drive rejected the access token.")
        if response.status_code == 404:
            # A genuinely different signal from "Drive is unavailable" — the
            # Execution Engine's permission validation (Phase 8) needs to
            # tell "this file no longer exists" apart from a transient
            # provider failure, since only one of those should ever be
            # retried.
            raise NotFoundError(f"Google Drive item not found: {url}.")
        if response.status_code == 429:
            raise DependencyUnavailableError("Google Drive rate limit exceeded.")
        if response.status_code == 403 and content_access:
            # A file's *content* can be 403 even though its metadata listed
            # fine — the owner disabled download/copy/print for viewers on
            # this specific item (a real, permanent Drive permission model
            # quirk, not a connector-wide problem). Distinct from the 403
            # branch below: this one will never succeed on retry and must
            # not be treated as "Drive is unavailable" for the whole job.
            raise ForbiddenError(f"Google Drive denied content access to file {url}.")
        if response.status_code == 403 and not content_access:
            # Drive represents *both* a genuine permission denial and a rate
            # limit as HTTP 403 (not just 429) — `error.errors[0].reason`
            # is the only way to tell them apart. Only a real permission
            # denial is permanent; an unrecognized or rate-limit reason
            # falls through to the retryable branch below, which is the
            # safe default (never silently drops a transient failure).
            reason = _drive_error_reason(response)
            rate_limit_reasons = (
                "rateLimitExceeded",
                "userRateLimitExceeded",
                "dailyLimitExceeded",
            )
            if reason is not None and reason not in rate_limit_reasons:
                raise ForbiddenError(f"Google Drive denied access ({reason}): {url}.")
        if response.status_code != 200:
            logger.warning(
                "google_drive_request_failed",
                extra={"status_code": response.status_code, "url": url},
            )
            raise DependencyUnavailableError(
                f"Google Drive request failed ({response.status_code})."
            )
        return response

    @staticmethod
    def _to_drive_file(item: dict) -> DriveFile:
        return DriveFile(
            id=item["id"],
            name=item.get("name", "untitled")[:_MAX_NAME_LENGTH],
            mime_type=item.get("mimeType", ""),
            parents=item.get("parents", []),
            size=int(item["size"]) if "size" in item else None,
            created_time=_parse_time(item.get("createdTime")),
            modified_time=_parse_time(item.get("modifiedTime")),
            viewed_by_me_time=_parse_time(item.get("viewedByMeTime")),
            owner_email=(item.get("owners") or [{}])[0].get("emailAddress"),
            shared=bool(item.get("shared", False)),
            checksum=item.get("md5Checksum"),
            version_id=item.get("headRevisionId"),
            is_folder=item.get("mimeType") == _FOLDER_MIME_TYPE,
            trashed=bool(item.get("trashed", False)),
            web_view_link=item.get("webViewLink"),
        )


def _drive_error_reason(response: requests.Response) -> str | None:
    """Best-effort read of Drive's `error.errors[0].reason` — safe to log
    (a fixed enum-like string, e.g. "insufficientFilePermissions", never
    request/token content), used only to tell a permanent permission denial
    apart from a 403-shaped rate limit."""
    try:
        errors = response.json().get("error", {}).get("errors", [])
    except ValueError:
        return None
    return errors[0].get("reason") if errors else None


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
