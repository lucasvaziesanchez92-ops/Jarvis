"""
JARVIS Files API — Railway Object Storage endpoints
Upload, download, list, and manage files in Railway Buckets.
"""

import os
import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form
from fastapi.responses import StreamingResponse, JSONResponse

from backend.core.storage import (
    upload_bytes,
    download_bytes,
    delete_file,
    list_files,
    generate_presigned_url,
    _get_s3_client,
    _get_bucket_name,
)

router = APIRouter(prefix="/files", tags=["files"])

ALLOWED_EXTENSIONS = {
    # Texto y Documentos
    ".txt", ".md", ".markdown", ".pdf", ".docx", ".csv",
    # Datos y Web
    ".json", ".xml", ".html", ".htm",
    # Hojas de cálculo
    ".xlsx", ".xls", ".ods",
    # Imágenes
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    # Audio y Video
    ".mp3", ".wav", ".webm", ".mp4", ".mov",
    # Código
    ".py", ".js", ".ts", ".jsx", ".tsx", ".cpp", ".h", ".hpp",
    ".html", ".css", ".scss", ".sql",
    ".yaml", ".yml", ".log", ".env", ".cfg", ".ini", ".toml",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def _generate_key(filename: str, folder: Optional[str] = None) -> str:
    """Generate a unique S3 object key."""
    ext = filename.split(".")[-1] if "." in filename else "bin"
    uid = uuid.uuid4().hex[:12]
    now = datetime.utcnow().strftime("%Y/%m/%d")
    base = f"{folder}/{now}" if folder else now
    return f"{base}/{uid}_{filename}"


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder: Optional[str] = Form(None),
    generate_url: bool = Form(True),
):
    """Upload a file to Railway Object Storage bucket."""
    # Validate extension
    ext = ("." + file.filename.split(".")[-1]).lower() if file.filename and "." in file.filename else ""
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Tipo de archivo no permitido: {ext}. Tipos permitidos: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Max: {MAX_FILE_SIZE / 1024 / 1024}MB")

    # Generate key
    key = _generate_key(file.filename or "unnamed", folder)

    # Upload
    try:
        upload_bytes(content, key, content_type=file.content_type)
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    # Build response
    response = {
        "key": key,
        "filename": file.filename,
        "size": len(content),
        "content_type": file.content_type,
        "uploaded_at": datetime.utcnow().isoformat(),
    }

    if generate_url:
        response["url"] = generate_presigned_url(key, expiration=3600)

    return response


@router.get("/download/{key:path}")
async def download_file_endpoint(key: str):
    """Download a file from the bucket by key."""
    try:
        data = download_bytes(key)
    except Exception:
        raise HTTPException(404, "File not found")

    return StreamingResponse(iter([data]), media_type="application/octet-stream")


@router.get("/list")
async def list_bucket_files(
    prefix: str = Query("", description="Filter by folder/prefix"),
    limit: int = Query(100, le=1000),
):
    """List files in the bucket."""
    try:
        items = list_files(prefix=prefix)
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    results = []
    for item in items[:limit]:
        results.append({
            "key": item["Key"],
            "size": item["Size"],
            "last_modified": item["LastModified"].isoformat() if hasattr(item["LastModified"], "isoformat") else str(item["LastModified"]),
        })

    return {"files": results, "count": len(results)}


@router.delete("/{key:path}")
async def delete_file_endpoint(key: str):
    """Delete a file from the bucket."""
    try:
        delete_file(key)
    except Exception:
        raise HTTPException(404, "File not found or could not delete")

    return {"deleted": True, "key": key}


@router.get("/url/{key:path}")
async def get_presigned_url(key: str, expiration: int = Query(3600, le=86400)):
    """Get a presigned URL for a file (temporary public access)."""
    try:
        url = generate_presigned_url(key, expiration=expiration)
    except Exception:
        raise HTTPException(404, "File not found")

    return {"url": url, "key": key, "expires_in": expiration}


@router.get("/health")
async def storage_health():
    """Check if Railway Object Storage is configured and accessible."""
    try:
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        s3.head_bucket(Bucket=bucket)
        return {"status": "ok", "bucket": bucket, "configured": True}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "configured": False, "detail": str(e)},
        )
