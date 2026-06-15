"""Google Suite agent tools — wrapped for LangGraph function calling."""
from langchain_core.tools import tool


@tool
def search_gmail(query: str) -> str:
    """Search emails in Gmail. Args: query (Gmail search syntax like 'from:user@example.com' or 'subject:meeting')."""
    from backend.services.gmail_service import search_emails
    try:
        results = search_emails(query, max_results=10)
        if not results:
            return "No se encontraron correos con esa búsqueda."
        lines = [f"{len(results)} correos encontrados:"]
        for e in results:
            lines.append(f"- [{e['date']}] {e['from']} | {e['subject']} | ID:{e['id']}")
        return "\n".join(lines)
    except RuntimeError as e:
        return str(e)


@tool
def send_gmail(to: str, subject: str, body: str) -> str:
    """Send an email via Gmail. Args: to, subject, body text."""
    from backend.services.gmail_service import send_email
    try:
        result = send_email(to, subject, body)
        return f"Correo enviado exitosamente a {to}. ID: {result['id']}"
    except RuntimeError as e:
        return str(e)


@tool
def list_gmail(max_results: int = 10) -> str:
    """List recent emails from inbox."""
    from backend.services.gmail_service import list_emails
    try:
        results = list_emails(max_results=max_results)
        if not results:
            return "No hay correos recientes."
        lines = [f"{len(results)} correos recientes:"]
        for e in results:
            lines.append(f"- [{e['date']}] {e['from']} | {e['subject']}")
        return "\n".join(lines)
    except RuntimeError as e:
        return str(e)


@tool
def get_gmail_detail(email_id: str) -> str:
    """Get the full body and headers of a single email by its ID. Use this after list_gmail to read the full content of a specific message."""
    from backend.services.gmail_service import get_email
    try:
        msg = get_email(email_id)
        return (
            f"From: {msg['from']}\n"
            f"To: {msg['to']}\n"
            f"Date: {msg['date']}\n"
            f"Subject: {msg['subject']}\n"
            f"\n{msg['body']}"
        )
    except RuntimeError as e:
        return str(e)


@tool
def delete_gmail_message(email_id: str) -> str:
    """Permanently delete a Gmail message by its ID. This cannot be undone."""
    from backend.services.gmail_service import delete_email
    try:
        result = delete_email(email_id)
        return f"Correo {email_id} eliminado permanentemente."
    except RuntimeError as e:
        return str(e)


@tool
def trash_gmail_message(email_id: str) -> str:
    """Move a Gmail message to trash (recoverable for 30 days). Use delete_gmail_message for permanent deletion."""
    from backend.services.gmail_service import trash_email
    try:
        result = trash_email(email_id)
        return f"Correo {email_id} movido a papelera."
    except Exception as e:
        return str(e)


@tool
def search_drive(query: str = "", mime_filter: str = "") -> str:
    """Search files in Google Drive.

    Args:
        query: keywords to match in file names (e.g. 'factura', 'informe').
               Leave empty to list all files.
        mime_filter: optional MIME-type filter. Common values:
                     'image/' (any image), 'image/png', 'image/jpeg',
                     'application/pdf', 'text/', 'application/vnd.google-apps.document'
                     (Google Docs), 'application/vnd.google-apps.spreadsheet'
                     (Google Sheets).
                     Leave empty to match any type.

    Returns: list of matching files with name, size, ID.
    """
    from backend.services.drive_service import list_files
    try:
        # If the user wants only images, build a query that the
        # Drive service can honour. list_files in the service
        # accepts a 'mime_type' filter parameter.
        kw = {"max_results": 20}
        if query:
            kw["query"] = query
        if mime_filter:
            kw["mime_type"] = mime_filter
        results = list_files(**kw)
        if not results:
            return (
                f"No se encontraron archivos en Drive"
                + (f" que coincidan con '{query}'" if query else "")
                + (f" de tipo '{mime_filter}'" if mime_filter else "")
                + "."
            )
        lines = ["archivos encontrados (MUESTRA SIEMPRE EL ENLACE EN MARKDOWN ASÍ: [Abrir](url)):"]
        for f in results:
            ftype = "📁" if f.get("mimeType") == "application/vnd.google-apps.folder" else "📄"
            size = f.get("size", "N/A")
            try:
                if isinstance(size, str) and size.isdigit():
                    size = f"{int(size)/1024:.1f}KB"
            except Exception:
                pass
            url = f.get("webViewLink", "")
            lines.append(f"- {ftype} {f['name']} ({size}) ID:{f['id']} URL:{url}")
        return "\n".join(lines)
    except Exception as e:
        return str(e)


@tool
def list_drive_files(max_results: int = 20) -> str:
    """List recent files from Google Drive root. Returns file names, IDs, types, and sizes."""
    from backend.services.drive_service import list_files
    try:
        results = list_files(max_results=max_results)
        if not results:
            return "No hay archivos en Drive."
        lines = ["archivos en Drive (MUESTRA SIEMPRE EL ENLACE EN MARKDOWN ASÍ: [Abrir](url)):"]
        for f in results:
            ftype = "📁" if f.get("mimeType") == "application/vnd.google-apps.folder" else "📄"
            size_str = f" ({int(f.get('size', 0)) / 1024:.0f}KB)" if f.get('size') else ""
            url = f.get("webViewLink", "")
            lines.append(f"- {ftype} {f['name']}{size_str} ID:{f['id']} URL:{url}")
        return "\n".join(lines)
    except Exception as e:
        return str(e)


@tool
def list_drive_folder(folder_id: str) -> str:
    """List files inside a specific Drive folder. Args: folder_id (Google Drive folder ID). Returns children with names and IDs."""
    from backend.services.drive_service import list_files, get_file_metadata
    try:
        parent = get_file_metadata(folder_id)
        parent_name = parent["name"] if parent else "carpeta"
        results = list_files(folder_id=folder_id, max_results=50)
        if not results:
            return f"No hay archivos en '{parent_name}'."
        lines = [f"📁 {parent_name} ({len(results)} elementos):"]
        for f in results:
            ftype = "📁" if f.get("mimeType") == "application/vnd.google-apps.folder" else "📄"
            lines.append(f"- {ftype} {f['name']} ID:{f['id']}")
        return "\n".join(lines)
    except RuntimeError as e:
        return str(e)


@tool
def read_drive_file(file_id: str) -> str:
    """Read and extract text content from a Google Drive file. Supports PDF, DOCX, XLSX, TXT, CSV, code files, and exports Google Docs/Sheets/Slides. Args: file_id (Drive file ID from list/search results). Returns full text content (up to 15000 chars)."""
    from backend.services.drive_service import read_file_content
    try:
        return read_file_content(file_id)
    except RuntimeError as e:
        return str(e)


@tool
def get_drive_file_info(file_id: str) -> str:
    """Get metadata for a single Drive file. Args: file_id. Returns name, type, size, modified date, and parent folder IDs."""
    from backend.services.drive_service import get_file_metadata
    try:
        meta = get_file_metadata(file_id)
        if not meta:
            return f"Archivo no encontrado: {file_id}"
        size_mb = int(meta.get("size", 0)) / 1024 / 1024 if meta.get("size") else 0
        return (
            f"📄 {meta['name']}\n"
            f"   Tipo: {meta.get('mimeType', 'desconocido')}\n"
            f"   Tamaño: {size_mb:.1f}MB\n"
            f"   Modificado: {meta.get('modifiedTime', 'N/A')[:10]}\n"
            f"   ID: {meta['id']}\n"
            f"   Carpeta padre: {meta.get('parents', ['root'])[0]}"
        )
    except RuntimeError as e:
        return str(e)


@tool
def upload_drive_file(filename: str, content: str, mime_type: str = "text/plain", folder_id: str = "") -> str:
    """Upload a file to Google Drive. Args: filename, content (text content of the file), mime_type (optional, default text/plain), folder_id (optional Google Drive folder ID). Use this to save notes, documents, code, or any text content to Drive."""
    from backend.services.drive_service import upload_file
    try:
        result = upload_file(filename, content.encode("utf-8"), mime_type, folder_id if folder_id else None)
        return f"Archivo subido a Drive: {result['name']} ({result['size']} bytes) ID:{result['id']}"
    except RuntimeError as e:
        return str(e)


@tool
def delete_drive_file(file_id: str) -> str:
    """Delete a file from Google Drive. Args: file_id (Google Drive file ID)."""
    from backend.services.drive_service import delete_file, get_file_metadata
    try:
        meta = get_file_metadata(file_id)
        name = meta["name"] if meta else file_id
        delete_file(file_id)
        return f"Archivo eliminado de Drive: {name}"
    except RuntimeError as e:
        return str(e)


@tool
def analyze_drive_image(file_id: str) -> str:
    """Analyze an image stored in Google Drive using Gemini Vision.
    Args: file_id: The Google Drive file ID of the image.
    Returns: A detailed visual description of the image.
    """
    from backend.services.drive_service import download_file
    import base64
    import os
    import requests
    try:
        data, filename, mime = download_file(file_id)
        if not mime.startswith("image/"):
            return f"Error: El archivo {filename} no es una imagen (tipo: {mime})."
            
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return "Error: GEMINI_API_KEY no configurada."

        b64 = base64.b64encode(data).decode("ascii")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Describe esta imagen en detalle en español. Qué ves? Objetos, personas, texto, colores, composición, contexto. Sé conciso pero completo."},
                    {"inline_data": {"mime_type": mime, "data": b64}}
                ]
            }]
        }
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return f"[Análisis de {filename}]: {text}"
    except Exception as e:
        return f"[Error al analizar imagen con Gemini: {str(e)[:200]}]"

@tool
def list_calendar_google(max_results: int = 10) -> str:
    """List upcoming events from Google Calendar."""
    from backend.services.calendar_service import list_events
    try:
        results = list_events(max_results=max_results)
        if not results:
            return "No hay eventos próximos en el calendario."
        lines = [f"{len(results)} eventos próximos:"]
        for e in results:
            lines.append(f"- {e['start']} → {e['end']} | {e['summary']}")
        return "\n".join(lines)
    except Exception as e:
        return str(e)


@tool
def create_calendar_event_google(summary: str = "Nueva Cita", start_time: str = "", end_time: str = "", description: str = "", location: str = "") -> str:
    """Create a Google Calendar event. Args: summary, start_time (ISO 8601), end_time (optional ISO 8601), optional description, optional location."""
    from backend.services.calendar_service import create_event
    try:
        if not start_time:
            return "Error: start_time es requerido."
        if not end_time:
            # Default to 1 hour after start_time if not provided
            from datetime import datetime, timedelta
            try:
                # Handle Z or timezone offsets by just taking the first 19 chars for simple 1-hour delta
                base = start_time[:19]
                dt = datetime.fromisoformat(base)
                end_time = (dt + timedelta(hours=1)).isoformat() + (start_time[19:] if len(start_time) > 19 else "")
            except Exception:
                end_time = start_time
        result = create_event(summary, start_time, end_time, description, location)
        return f"Evento creado: {result['summary']} ({result['id']})"
    except Exception as e:
        return str(e)
