"""S3-compatible backup service for JARVIS data."""
import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from backend.config import settings

logger = __import__('loguru').logger


class BackupConfig:
    """Configuracion de backup S3."""

    def __init__(
        self,
        provider: str = "backblaze",  # backblaze, cloudflare_r2, aws_s3, minio
        bucket: str = "",
        region: str = "us-west-002",
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        prefix: str = "jarvis-backups",
    ):
        self.provider = provider
        self.bucket = bucket
        self.region = region
        self.endpoint = endpoint
        self.access_key = access_key or os.getenv("S3_ACCESS_KEY", "")
        self.secret_key = secret_key or os.getenv("S3_SECRET_KEY", "")
        self.prefix = prefix


def _get_backup_config() -> BackupConfig:
    """Obtener configuracion de backup desde settings o env."""
    provider = os.getenv("S3_PROVIDER", "backblaze")
    bucket = os.getenv("S3_BUCKET", "")
    region = os.getenv("S3_REGION", "us-west-002")
    endpoint = os.getenv("S3_ENDPOINT", None)

    return BackupConfig(
        provider=provider,
        bucket=bucket,
        region=region,
        endpoint=endpoint,
    )


def _get_s3_client(config: BackupConfig):
    """Crear cliente S3 segun el provider."""
    if config.provider == "backblaze":
        endpoint = config.endpoint or f"https://s3.{config.region}.backblazeb2.com"
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name=config.region,
        )
    elif config.provider == "cloudflare_r2":
        endpoint = config.endpoint or "https://xxx.r2.cloudflarestorage.com"
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name="auto",
        )
    elif config.provider == "aws_s3":
        return boto3.client(
            "s3",
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name=config.region,
        )
    else:
        return boto3.client(
            "s3",
            endpoint_url=config.endpoint,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name=config.region,
        )


def _compute_file_hash(filepath: str) -> str:
    """Calcular SHA256 de un archivo."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _backup_file_to_s3(
    client,
    bucket: str,
    local_path: str,
    s3_key: str,
    content_type: str = "application/octet-stream",
) -> dict:
    """Subir un archivo a S3 con metadatos."""
    try:
        extra_args = {
            "ContentType": content_type,
            "Metadata": {
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "original_path": local_path,
            },
        }
        client.upload_file(local_path, bucket, s3_key, ExtraArgs=extra_args)

        response = client.head_object(Bucket=bucket, Key=s3_key)
        return {
            "key": s3_key,
            "size": response["ContentLength"],
            "etag": response["ETag"],
            "uploaded_at": response["Metadata"].get("uploaded_at", ""),
        }
    except ClientError as e:
        logger.error(f"S3 upload failed for {local_path}: {e}")
        raise


def backup_notes_to_s3(notes_data: list[dict], backup_name: Optional[str] = None) -> dict:
    """
    Guardar notes como JSON en S3.
    Returns: { backup_key, notes_count, size_bytes, uploaded_at }
    """
    config = _get_backup_config()
    if not config.bucket or not config.access_key:
        return {"error": "S3 not configured. Set S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY"}

    if not backup_name:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"notes_{timestamp}.json"

    s3_key = f"{config.prefix}/notes/{backup_name}"

    temp_file = f"data/temp_notes_{int(datetime.now(timezone.utc).timestamp())}.json"
    os.makedirs("data/temp", exist_ok=True)

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": "1.0",
                    "backup_type": "notes",
                    "backup_at": datetime.now(timezone.utc).isoformat(),
                    "notes_count": len(notes_data),
                    "notes": notes_data,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        client = _get_s3_client(config)
        result = _backup_file_to_s3(
            client,
            config.bucket,
            temp_file,
            s3_key,
            content_type="application/json",
        )

        return {
            "backup_key": s3_key,
            "notes_count": len(notes_data),
            "size_bytes": result["size"],
            "uploaded_at": result["uploaded_at"],
        }

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def backup_todos_to_s3(todos_data: list[dict], backup_name: Optional[str] = None) -> dict:
    """Guardar todos como JSON en S3."""
    config = _get_backup_config()
    if not config.bucket or not config.access_key:
        return {"error": "S3 not configured. Set S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY"}

    if not backup_name:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"todos_{timestamp}.json"

    s3_key = f"{config.prefix}/todos/{backup_name}"

    temp_file = f"data/temp_todos_{int(datetime.now(timezone.utc).timestamp())}.json"
    os.makedirs("data/temp", exist_ok=True)

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": "1.0",
                    "backup_type": "todos",
                    "backup_at": datetime.now(timezone.utc).isoformat(),
                    "todos_count": len(todos_data),
                    "todos": todos_data,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        client = _get_s3_client(config)
        result = _backup_file_to_s3(
            client,
            config.bucket,
            temp_file,
            s3_key,
            content_type="application/json",
        )

        return {
            "backup_key": s3_key,
            "todos_count": len(todos_data),
            "size_bytes": result["size"],
            "uploaded_at": result["uploaded_at"],
        }

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def list_s3_backups(backup_type: str = "notes") -> list[dict]:
    """Listar backups disponibles en S3."""
    config = _get_backup_config()
    if not config.bucket or not config.access_key:
        return []

    try:
        client = _get_s3_client(config)
        prefix = f"{config.prefix}/{backup_type}/"

        response = client.list_objects_v2(Bucket=config.bucket, Prefix=prefix)

        backups = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            backups.append(
                {
                    "key": key,
                    "size_bytes": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat() if obj.get("LastModified") else None,
                    "etag": obj["ETag"],
                }
            )

        return sorted(backups, key=lambda x: x["last_modified"] or "", reverse=True)

    except ClientError as e:
        logger.error(f"List S3 backups failed: {e}")
        return []


def download_backup_from_s3(backup_key: str, local_path: str) -> dict:
    """Descargar un backup especifico de S3."""
    config = _get_backup_config()
    if not config.bucket or not config.access_key:
        return {"error": "S3 not configured"}

    try:
        client = _get_s3_client(config)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        client.download_file(config.bucket, backup_key, local_path)

        return {"downloaded_to": local_path, "key": backup_key}

    except ClientError as e:
        logger.error(f"S3 download failed for {backup_key}: {e}")
        return {"error": str(e)}


def full_backup() -> dict:
    """Ejecutar backup completo de notes y todos."""
    from backend.services.notes_service import list_notes
    from backend.services.todos_service import list_todos

    notes = list_notes()
    todos = list_todos()

    notes_result = backup_notes_to_s3(notes)
    todos_result = backup_todos_to_s3(todos)

    return {
        "notes_backup": notes_result,
        "todos_backup": todos_result,
        "full_backup_at": datetime.now(timezone.utc).isoformat(),
    }


def check_s3_connection() -> dict:
    """Verificar que S3 esta configurado y accesible."""
    config = _get_backup_config()

    if not config.bucket:
        return {"status": "not_configured", "message": "S3_BUCKET not set"}

    if not config.access_key or not config.secret_key:
        return {"status": "not_configured", "message": "S3 credentials not set"}

    try:
        client = _get_s3_client(config)
        client.head_bucket(Bucket=config.bucket)
        return {
            "status": "connected",
            "provider": config.provider,
            "bucket": config.bucket,
        }
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        return {"status": "error", "error_code": error_code, "message": str(e)}