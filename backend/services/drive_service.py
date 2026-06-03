"""Google Drive service — upload, list, download, delete files. Reemplaza Railway bucket."""
import io
from typing import Optional

from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from loguru import logger

from backend.services.google_auth import GoogleAuthService, get_refresh_token

DEFAULT_USER = "default_user"


def _get_drive_service(user_id: str = DEFAULT_USER):
    token = get_refresh_token(user_id)
    if not token:
        raise RuntimeError("Google no está conectado. Hacé login en Google primero.")
    creds = GoogleAuthService.get_credentials(token)
    return GoogleAuthService.build_drive(creds)


def list_files(query: str = "", max_results: int = 50, user_id: str = DEFAULT_USER) -> list[dict]:
    """List files from Google Drive."""
    service = _get_drive_service(user_id)
    q = "trashed = false"
    if query:
        q += f" and (name contains '{query}' or fullText contains '{query}')"
    results = service.files().list(
        q=q,
        pageSize=max_results,
        fields="files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink,thumbnailLink)",
    ).execute()
    return results.get("files", [])


def upload_file(filename: str, data: bytes, mime_type: str = "application/octet-stream", folder_id: Optional[str] = None, user_id: str = DEFAULT_USER) -> dict:
    """Upload a file to Google Drive."""
    service = _get_drive_service(user_id)
    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=True)
    uploaded = service.files().create(body=file_metadata, media_body=media, fields="id,name,size,webViewLink").execute()
    return {"id": uploaded["id"], "name": uploaded["name"], "size": uploaded.get("size", 0), "url": uploaded.get("webViewLink", "")}


def download_file(file_id: str, user_id: str = DEFAULT_USER) -> tuple[bytes, str]:
    """Download a file from Google Drive. Returns (bytes, filename)."""
    service = _get_drive_service(user_id)
    meta = service.files().get(fileId=file_id, fields="name,mimeType").execute()
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue(), meta.get("name", file_id)


def delete_file(file_id: str, user_id: str = DEFAULT_USER):
    """Delete a file from Google Drive."""
    service = _get_drive_service(user_id)
    service.files().delete(fileId=file_id).execute()


def create_folder(name: str, parent_id: Optional[str] = None, user_id: str = DEFAULT_USER) -> dict:
    """Create a folder in Google Drive."""
    service = _get_drive_service(user_id)
    file_metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        file_metadata["parents"] = [parent_id]
    folder = service.files().create(body=file_metadata, fields="id,name").execute()
    return folder
