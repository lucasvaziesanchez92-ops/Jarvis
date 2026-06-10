"""Google Drive API router — replace Railway bucket."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from loguru import logger
from backend.services import drive_service
from backend.services.google_auth import GoogleNotConfiguredError

router = APIRouter(prefix="/drive", tags=["drive"])


def _handle_drive_error(e: Exception) -> HTTPException:
    """Map any error to a clean HTTP response. Google not configured = 503,
    anything else = 500 with the message. We log the full traceback for 500s."""
    if isinstance(e, GoogleNotConfiguredError):
        return HTTPException(503, str(e))
    if isinstance(e, RuntimeError) and ("Google" in str(e) or "credentials" in str(e).lower() or "OAuth" in str(e)):
        return HTTPException(503, f"Google Drive no configurado: {e}")
    logger.exception(f"Drive endpoint failed: {e}")
    return HTTPException(500, f"Drive error: {type(e).__name__}: {e}")


@router.get("/list")
async def list_files(max_results: int = Query(50, le=200)):
    try:
        return drive_service.list_files(max_results=max_results)
    except Exception as e:
        raise _handle_drive_error(e)


@router.post("/upload")
async def upload(file: UploadFile = File(...), folder: Optional[str] = Form(None)):
    try:
        data = await file.read()
        result = drive_service.upload_file(file.filename or "unnamed", data, file.content_type or "application/octet-stream", folder)
        return result
    except Exception as e:
        raise _handle_drive_error(e)


@router.get("/download/{file_id}")
async def download(file_id: str):
    try:
        data, filename, mime = drive_service.download_file(file_id)
        return StreamingResponse(iter([data]), media_type=mime or "application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except Exception as e:
        raise _handle_drive_error(e)


@router.delete("/{file_id}")
async def delete(file_id: str):
    try:
        drive_service.delete_file(file_id)
        return {"deleted": True, "file_id": file_id}
    except Exception as e:
        raise _handle_drive_error(e)


@router.get("/health")
async def health():
    """Health: returns 'configured' reflecting whether OAuth is set up."""
    try:
        from backend.services.google_auth import _ensure_config
        _ensure_config()
        return {"service": "google-drive", "configured": True}
    except GoogleNotConfiguredError as e:
        return {"service": "google-drive", "configured": False, "reason": str(e)}
