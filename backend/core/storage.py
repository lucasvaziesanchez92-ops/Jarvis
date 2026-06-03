"""
JARVIS File Storage — Railway Object Storage (S3) + Local fallback
Si Railway no está configurado, usa almacenamiento local en data/uploads/.
"""
import os
import json
import shutil
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

try:
    import boto3
    from botocore.client import Config
    _S3_AVAILABLE = True
except ImportError:
    _S3_AVAILABLE = False

_LOCAL_STORAGE_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"
_LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
_LOCAL_META_FILE = _LOCAL_STORAGE_DIR / "_files.json"


def _is_railway_configured() -> bool:
    endpoint = (os.environ.get("ENDPOINT")
             or os.environ.get("RAILWAY_BUCKET_ENDPOINT")
             or os.environ.get("AWS_ENDPOINT_URL"))
    access_key = (os.environ.get("ACCESS_KEY_ID")
               or os.environ.get("AWS_ACCESS_KEY_ID")
               or os.environ.get("RAILWAY_BUCKET_ACCESS_KEY"))
    secret_key = (os.environ.get("SECRET_ACCESS_KEY")
               or os.environ.get("AWS_SECRET_ACCESS_KEY")
               or os.environ.get("RAILWAY_BUCKET_SECRET_KEY"))
    return bool(endpoint and access_key and secret_key)


def _get_s3_client():
    if not _S3_AVAILABLE:
        raise RuntimeError("boto3 no instalado.")
    endpoint = (os.environ.get("ENDPOINT")
             or os.environ.get("RAILWAY_BUCKET_ENDPOINT")
             or os.environ.get("AWS_ENDPOINT_URL"))
    access_key = (os.environ.get("ACCESS_KEY_ID")
               or os.environ.get("AWS_ACCESS_KEY_ID")
               or os.environ.get("RAILWAY_BUCKET_ACCESS_KEY"))
    secret_key = (os.environ.get("SECRET_ACCESS_KEY")
               or os.environ.get("AWS_SECRET_ACCESS_KEY")
               or os.environ.get("RAILWAY_BUCKET_SECRET_KEY"))
    if not all([endpoint, access_key, secret_key]):
        raise RuntimeError("Railway Object Storage no configurado.")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )


def _get_bucket_name():
    return (os.environ.get("BUCKET")
         or os.environ.get("RAILWAY_BUCKET_NAME")
         or os.environ.get("AWS_S3_BUCKET_NAME")
         or "jarvis-uploads")


def _load_local_meta() -> dict:
    if _LOCAL_META_FILE.exists():
        return json.loads(_LOCAL_META_FILE.read_text(encoding="utf-8"))
    return {"files": {}}


def _save_local_meta(meta: dict):
    _LOCAL_META_FILE.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def upload_bytes(data: bytes, object_key: str, content_type: Optional[str] = None) -> str:
    if _is_railway_configured():
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        extra = {}
        if content_type:
            extra["ContentType"] = content_type
        s3.put_object(Bucket=bucket, Key=object_key, Body=data, **extra)
        endpoint = os.environ.get("ENDPOINT") or os.environ.get("RAILWAY_BUCKET_ENDPOINT")
        return f"{endpoint}/{bucket}/{object_key}"

    # Local fallback
    file_path = _LOCAL_STORAGE_DIR / object_key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(data)
    meta = _load_local_meta()
    meta["files"][object_key] = {
        "size": len(data),
        "content_type": content_type,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_local_meta(meta)
    return str(file_path)


def download_bytes(object_key: str) -> bytes:
    if _is_railway_configured():
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        response = s3.get_object(Bucket=bucket, Key=object_key)
        return response["Body"].read()

    # Local fallback
    file_path = _LOCAL_STORAGE_DIR / object_key
    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {object_key}")
    return file_path.read_bytes()


def delete_file(object_key: str):
    if _is_railway_configured():
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        s3.delete_object(Bucket=bucket, Key=object_key)
        return

    # Local fallback
    file_path = _LOCAL_STORAGE_DIR / object_key
    if file_path.exists():
        file_path.unlink()
    meta = _load_local_meta()
    meta["files"].pop(object_key, None)
    _save_local_meta(meta)


def list_files(prefix: str = "") -> list[dict]:
    if _is_railway_configured():
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return response.get("Contents", [])

    # Local fallback
    meta = _load_local_meta()
    results = []
    for key, info in meta["files"].items():
        if prefix and not key.startswith(prefix):
            continue
        results.append({
            "Key": key,
            "Size": info["size"],
            "LastModified": info["uploaded_at"],
        })
    results.sort(key=lambda x: x["LastModified"], reverse=True)
    return results


def generate_presigned_url(object_key: str, expiration: int = 3600) -> str:
    if _is_railway_configured():
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=expiration,
        )
    return f"/api/files/download/{object_key}"
