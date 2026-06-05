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

_MAGIC_SIGNATURES = {
    # Extension -> [(offset, bytes_hex), ...]
    ".pdf":  [(0, "25504446")],
    ".png":  [(0, "89504e47")],
    ".jpg":  [(0, "ffd8")],
    ".jpeg": [(0, "ffd8")],
    ".gif":  [(0, "47494638")],
    ".webp": [(0, "52494646")],  # RIFF container, weak check
    ".mp3":  [(0, "fffb"), (0, "fff3"), (0, "fffa"), (0, "494433")],  # MP3 or ID3
    ".wav":  [(0, "52494646")],
    ".mp4":  [(4, "66747970")],
    ".mov":  [(4, "66747970")],
    ".webm": [(0, "1a45dfa3")],
    ".docx": [(0, "504b0304")],
    ".xlsx": [(0, "504b0304")],
    ".ods":  [(0, "504b0304")],
}


def _validate_magic_bytes(data: bytes, ext: str) -> bool:
    """Check file magic bytes match expected extension. Returns True if valid or unknown ext."""
    signatures = _MAGIC_SIGNATURES.get(ext)
    if not signatures:
        return True
    for offset, expected_hex in signatures:
        end = offset + len(expected_hex) // 2
        if len(data) >= end and data[offset:end].hex() == expected_hex:
            return True
    return False


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
    # Validate extension + check magic bytes
    filename = file.filename or "unnamed"
    ext = ("." + filename.split(".")[-1]).lower() if "." in filename else ""
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Tipo de archivo no permitido: {ext}. Tipos permitidos: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Max: {MAX_FILE_SIZE / 1024 / 1024}MB")

    if not _validate_magic_bytes(content, ext):
        raise HTTPException(400, f"El contenido del archivo no coincide con la extensión {ext}. Rechazado por seguridad.")

    key = _generate_key(filename, folder)

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


def _sanitize_key(key: str) -> str:
    sanitized = key.replace("\\", "/")
    parts = [p for p in sanitized.split("/") if p and p not in (".", "..")]
    return "/".join(parts)


@router.get("/download/{key:path}")
async def download_file_endpoint(key: str):
    """Download a file from the bucket by key."""
    try:
        data = download_bytes(_sanitize_key(key))
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
        delete_file(_sanitize_key(key))
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
