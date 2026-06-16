"""Google Drive service — upload, list, download, read, delete files with auto-refresh."""
import io
import zipfile
from typing import Optional

from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from loguru import logger

from backend.services.google_auth import (
    GoogleAuthService, GoogleNotConfiguredError,
    get_token_pair, save_tokens, get_refresh_token, _ensure_config,
)

DEFAULT_USER = "default_user"
MAX_FILE_BYTES = 10 * 1024 * 1024
EXPORT_FORMATS = {
    "application/vnd.google-apps.document":     "text/plain",
    "application/vnd.google-apps.spreadsheet":  "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


def _get_drive_service(user_id: str = DEFAULT_USER):
    _ensure_config()
    refresh_token, access_token, expires_at = get_token_pair(user_id)
    if not refresh_token:
        raise RuntimeError("Google no está conectado. Hacé login en Google primero.")
    creds = GoogleAuthService.get_credentials(refresh_token, access_token, expires_at)
    return GoogleAuthService.build_drive(creds)


def list_files(query: str = "", max_results: int = 50, folder_id: Optional[str] = None, mime_type: str = "", user_id: str = DEFAULT_USER) -> list[dict]:
    """List files. If folder_id is set, list children of that folder. Otherwise list from root.

    Args:
        query: substring to match in file name or fullText.
        max_results: cap.
        folder_id: restrict to children of this folder.
        mime_type: MIME-type filter. If set with no '/' suffix
                   (e.g. 'image'), matches all MIME types starting
                   with that prefix. If set WITH '/' (e.g.
                   'image/png'), matches exactly that MIME type.
    """
    service = _get_drive_service(user_id)
    q = "trashed = false"
    if folder_id:
        q += f" and '{folder_id}' in parents"
    if query:
        # Escape single quotes in user input
        safe = query.replace("'", "\\'")
        q += f" and (name contains '{safe}' or fullText contains '{safe}')"
    if mime_type:
        safe_mime = mime_type.replace("'", "\\'")
        if "/" in safe_mime:
            q += f" and mimeType = '{safe_mime}'"
        else:
            q += f" and mimeType contains '{safe_mime}/'"

    kwargs = {
        "q": q,
        "pageSize": max_results,
        "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink,thumbnailLink,parents)"
    }
    # Google Drive API doesn't support orderBy when using fullText search
    if not query:
        kwargs["orderBy"] = "folder,name"

    results = service.files().list(**kwargs).execute()
    return results.get("files", [])


def get_file_metadata(file_id: str, user_id: str = DEFAULT_USER) -> dict | None:
    """Get a single file's metadata. Returns None if not found."""
    service = _get_drive_service(user_id)
    try:
        return service.files().get(
            fileId=file_id,
            fields="id,name,mimeType,size,createdTime,modifiedTime,webViewLink,parents",
        ).execute()
    except Exception as e:
        logger.warning(f"Drive metadata fetch failed for {file_id}: {e}")
        return None


def upload_file(filename: str, data: bytes, mime_type: str = "application/octet-stream", folder_id: Optional[str] = None, user_id: str = DEFAULT_USER) -> dict:
    service = _get_drive_service(user_id)
    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=True)
    uploaded = service.files().create(body=file_metadata, media_body=media, fields="id,name,size,webViewLink").execute()
    return {"id": uploaded["id"], "name": uploaded["name"], "size": uploaded.get("size", 0), "url": uploaded.get("webViewLink", "")}


def download_file(file_id: str, user_id: str = DEFAULT_USER) -> tuple[bytes, str, str]:
    """Download a file from Drive. Returns (bytes, filename, mimeType). Exports Google Docs natively. Zips folders."""
    service = _get_drive_service(user_id)
    meta = service.files().get(fileId=file_id, fields="name,mimeType,size").execute()
    mime = meta.get("mimeType", "")
    filename = meta.get("name", file_id)

    if mime == "application/vnd.google-apps.folder":
        return _download_folder_as_zip(service, file_id, filename)

    if mime in EXPORT_FORMATS:
        export_mime = EXPORT_FORMATS[mime]
        logger.info(f"Exporting Google Workspace file {file_id} as {export_mime}")
        data = service.files().export(fileId=file_id, mimeType=export_mime).execute()
        return data, filename, export_mime

    size = int(meta.get("size", 0))
    if size > MAX_FILE_BYTES:
        raise RuntimeError(f"Archivo demasiado grande: {size / 1024 / 1024:.1f}MB. Límite: {MAX_FILE_BYTES / 1024 / 1024:.0f}MB.")

    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue(), filename, mime

def _download_folder_as_zip(service, folder_id: str, folder_name: str) -> tuple[bytes, str, str]:
    """Downloads the immediate children of a folder and zips them. Limits to 50 files and max size."""
    logger.info(f"Downloading folder {folder_name} as ZIP")
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        pageSize=50,
        fields="files(id,name,mimeType,size)"
    ).execute()
    children = results.get("files", [])
    
    zip_buffer = io.BytesIO()
    total_size = 0
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for child in children:
            if child.get("mimeType") == "application/vnd.google-apps.folder":
                continue # Skip subfolders for simplicity/safety
            
            c_id = child["id"]
            c_name = child["name"]
            c_mime = child.get("mimeType", "")
            
            # Export if needed
            if c_mime in EXPORT_FORMATS:
                export_mime = EXPORT_FORMATS[c_mime]
                try:
                    c_data = service.files().export(fileId=c_id, mimeType=export_mime).execute()
                    if c_mime == "application/vnd.google-apps.document": c_name += ".txt"
                    elif c_mime == "application/vnd.google-apps.spreadsheet": c_name += ".csv"
                    elif c_mime == "application/vnd.google-apps.presentation": c_name += ".txt"
                    zf.writestr(c_name, c_data)
                    total_size += len(c_data)
                except Exception as e:
                    logger.warning(f"Failed to export {c_name}: {e}")
                continue
                
            c_size = int(child.get("size", 0))
            if c_size > 10 * 1024 * 1024:
                logger.warning(f"Skipping {c_name} in ZIP because it's too large ({c_size} bytes)")
                continue
                
            if total_size + c_size > MAX_FILE_BYTES:
                logger.warning(f"ZIP size limit reached, skipping remaining files.")
                break
                
            try:
                request = service.files().get_media(fileId=c_id)
                buf = io.BytesIO()
                downloader = MediaIoBaseDownload(buf, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                data = buf.getvalue()
                zf.writestr(c_name, data)
                total_size += len(data)
            except Exception as e:
                logger.warning(f"Failed to download {c_name} for ZIP: {e}")
                
    return zip_buffer.getvalue(), f"{folder_name}.zip", "application/zip"


def read_file_content(file_id: str, user_id: str = DEFAULT_USER) -> str:
    """Download a Drive file and extract its text content using file_extractor."""
    from backend.core.file_extractor import extract_text_from_bytes

    meta = get_file_metadata(file_id, user_id)
    if not meta:
        return f"[Error: archivo con ID {file_id} no encontrado en Drive.]"

    filename = meta["name"]
    mime = meta.get("mimeType", "")
    size = int(meta.get("size", 0))

    if mime in EXPORT_FORMATS:
        export_mime = EXPORT_FORMATS[mime]
        service = _get_drive_service(user_id)
        data = service.files().export(fileId=file_id, mimeType=export_mime).execute()
        return extract_text_from_bytes(data, filename) or f"[Archivo Google Workspace exportado como {export_mime}, {len(data)} bytes.]"

    if size > MAX_FILE_BYTES:
        return f"[Archivo demasiado grande: {filename} ({size / 1024 / 1024:.1f}MB). Límite: {MAX_FILE_BYTES / 1024 / 1024:.0f}MB.]"

    try:
        data, _, _ = download_file(file_id, user_id)
        return extract_text_from_bytes(data, filename) or f"[Archivo binario sin texto extraíble: {filename}]"
    except Exception as e:
        return f"[Error al leer {filename}: {e}]"


def delete_file(file_id: str, user_id: str = DEFAULT_USER):
    service = _get_drive_service(user_id)
    service.files().delete(fileId=file_id).execute()


def create_folder(name: str, parent_id: Optional[str] = None, user_id: str = DEFAULT_USER) -> dict:
    service = _get_drive_service(user_id)
    file_metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        file_metadata["parents"] = [parent_id]
    folder = service.files().create(body=file_metadata, fields="id,name").execute()
    return folder
