from datetime import UTC, datetime

from vault_shared.connectors.google_drive import DriveFile
from vault_shared.db.models import ExecutionActionType
from worker.execution.execution_service import ExecutionService


def _drive_file(*, name: str = "Doc.txt", parents: list[str] | None = None, trashed: bool = False) -> DriveFile:
    now = datetime.now(UTC)
    return DriveFile(
        id="f-1",
        name=name,
        mime_type="text/plain",
        parents=["folder-a"] if parents is None else parents,
        size=100,
        created_time=now,
        modified_time=now,
        viewed_by_me_time=None,
        owner_email="founder@acme.com",
        shared=False,
        checksum=None,
        version_id=None,
        is_folder=False,
        trashed=trashed,
    )


def test_pre_mutation_state_for_archive_captures_untrashed() -> None:
    state = ExecutionService._pre_mutation_state(ExecutionActionType.ARCHIVE, _drive_file())
    assert state == {"trashed": False}


def test_pre_mutation_state_for_remove_duplicate_captures_untrashed() -> None:
    state = ExecutionService._pre_mutation_state(ExecutionActionType.REMOVE_DUPLICATE, _drive_file())
    assert state == {"trashed": False}


def test_pre_mutation_state_for_rename_captures_the_current_name() -> None:
    state = ExecutionService._pre_mutation_state(
        ExecutionActionType.RENAME, _drive_file(name="Original.txt")
    )
    assert state == {"name": "Original.txt"}


def test_pre_mutation_state_for_move_file_captures_the_current_parent() -> None:
    state = ExecutionService._pre_mutation_state(
        ExecutionActionType.MOVE_FILE, _drive_file(parents=["folder-a", "folder-b"])
    )
    assert state == {"parent_folder_id": "folder-a"}


def test_pre_mutation_state_for_move_folder_with_no_parents_is_none() -> None:
    state = ExecutionService._pre_mutation_state(
        ExecutionActionType.MOVE_FOLDER, _drive_file(parents=[])
    )
    assert state == {"parent_folder_id": None}


def test_pre_mutation_state_for_update_metadata_is_empty() -> None:
    state = ExecutionService._pre_mutation_state(ExecutionActionType.UPDATE_METADATA, _drive_file())
    assert state == {}
