"""REST endpoints for S3 backup operations."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.backup_service import (
    backup_notes_to_s3,
    backup_todos_to_s3,
    full_backup,
    list_s3_backups,
    download_backup_from_s3,
    check_s3_connection,
)

router = APIRouter()


class BackupNotesRequest(BaseModel):
    backup_name: str | None = None


class BackupTodosRequest(BaseModel):
    backup_name: str | None = None


class DownloadBackupRequest(BaseModel):
    backup_key: str


class BackupResponse(BaseModel):
    backup_key: str | None = None
    notes_count: int | None = None
    todos_count: int | None = None
    size_bytes: int | None = None
    uploaded_at: str | None = None
    error: str | None = None


@router.get("/backup/status")
def backup_status():
    return check_s3_connection()


@router.post("/backup/notes", response_model=BackupResponse)
def backup_notes(body: BackupNotesRequest | None = None):
    from backend.services.notes_service import list_notes
    notes = list_notes()
    result = backup_notes_to_s3(notes, body.backup_name if body else None)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/backup/todos", response_model=BackupResponse)
def backup_todos(body: BackupTodosRequest | None = None):
    from backend.services.todos_service import list_todos
    todos = list_todos()
    result = backup_todos_to_s3(todos, body.backup_name if body else None)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/backup/full")
def full_backup_endpoint():
    return full_backup()


@router.get("/backup/list/{backup_type}")
def list_backups(backup_type: str):
    if backup_type not in ("notes", "todos"):
        raise HTTPException(status_code=400, detail="backup_type must be 'notes' or 'todos'")
    return list_s3_backups(backup_type)


@router.post("/backup/restore")
def restore_backup(body: DownloadBackupRequest):
    import os
    local_path = f"data/restore_{body.backup_key.split('/')[-1]}"
    result = download_backup_from_s3(body.backup_key, local_path)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result