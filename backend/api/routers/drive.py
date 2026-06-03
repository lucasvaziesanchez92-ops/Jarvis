"""Google Drive API router — replace Railway bucket."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from backend.services import drive_service

router = APIRouter(prefix="/drive", tags=["drive"])

@router.get("/list")
async def list_files(max_results: int = Query(50, le=200)):
    try:
        return drive_service.list_files(max_results=max_results)
    except RuntimeError as e:
        raise HTTPException(401, str(e))

@router.post("/upload")
async def upload(file: UploadFile = File(...), folder: Optional[str] = Form(None)):
    try:
        data = await file.read()
        result = drive_service.upload_file(file.filename or "unnamed", data, file.content_type or "application/octet-stream", folder)
        return result
    except RuntimeError as e:
        raise HTTPException(401, str(e))

@router.get("/download/{file_id}")
async def download(file_id: str):
    try:
        data, filename = drive_service.download_file(file_id)
        return StreamingResponse(iter([data]), media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except RuntimeError as e:
        raise HTTPException(401, str(e))

@router.delete("/{file_id}")
async def delete(file_id: str):
    try:
        drive_service.delete_file(file_id)
        return {"deleted": True, "file_id": file_id}
    except RuntimeError as e:
        raise HTTPException(401, str(e))

@router.get("/health")
async def health():
    return {"service": "google-drive", "configured": True}
