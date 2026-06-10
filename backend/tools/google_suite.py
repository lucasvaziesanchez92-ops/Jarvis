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
def search_drive(query: str) -> str:
    """Search files in Google Drive. Args: query keywords. Returns file names, IDs, and types."""
    from backend.services.drive_service import list_files
    try:
        results = list_files(query=query, max_results=20)
        if not results:
            return "No se encontraron archivos en Drive."
        lines = [f"{len(results)} archivos encontrados:"]
        for f in results:
            ftype = "📁" if f.get("mimeType") == "application/vnd.google-apps.folder" else "📄"
            lines.append(f"- {ftype} {f['name']} ({f.get('size', 'N/A')} bytes) ID:{f['id']}")
        return "\n".join(lines)
    except RuntimeError as e:
        return str(e)


@tool
def list_drive_files(max_results: int = 20) -> str:
    """List recent files from Google Drive root. Returns file names, IDs, types, and sizes."""
    from backend.services.drive_service import list_files
    try:
        results = list_files(max_results=max_results)
        if not results:
            return "No hay archivos en Drive."
        lines = [f"{len(results)} archivos en Drive:"]
        for f in results:
            ftype = "📁" if f.get("mimeType") == "application/vnd.google-apps.folder" else "📄"
            size_str = f" ({int(f.get('size', 0)) / 1024:.0f}KB)" if f.get("size") else ""
            lines.append(f"- {ftype} {f['name']}{size_str} ID:{f['id']}")
        return "\n".join(lines)
    except RuntimeError as e:
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
    """Analyze an image from Google Drive using AI vision (Groq). Args: file_id (Drive file ID of an image — jpg, png, gif, webp). Returns a detailed description of what's in the image: objects, people, text, colors, layout, etc."""
    from backend.services.drive_service import download_file
    import base64, os
    try:
        data, filename, mime = download_file(file_id)
    except RuntimeError as e:
        return str(e)

    if not mime.startswith("image/"):
        return f"El archivo '{filename}' no es una imagen (tipo: {mime}). Usá read_drive_file para archivos de texto."

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        return f"[Vision no disponible: GROQ_API_KEY no configurada. Imagen: {filename}, {len(data)} bytes.]"

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        b64 = base64.b64encode(data).decode("ascii")
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe esta imagen en detalle en español. Qué ves? Objetos, personas, texto, colores, composición, contexto. Sé conciso pero completo."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ]
            }],
            max_tokens=500,
            temperature=0.3,
        )
        return f"[Análisis de {filename}]: {completion.choices[0].message.content}"
    except Exception as e:
        return f"[Error al analizar imagen {filename} con Groq Vision: {str(e)[:200]}]"


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
    except RuntimeError as e:
        return str(e)


@tool
def create_calendar_event_google(summary: str, start_time: str, end_time: str, description: str = "", location: str = "") -> str:
    """Create a Google Calendar event. Args: summary, start_time (ISO 8601), end_time (ISO 8601), optional description, optional location."""
    from backend.services.calendar_service import create_event
    try:
        result = create_event(summary, start_time, end_time, description, location)
        return f"Evento creado: {result['summary']} ({result['id']})"
    except RuntimeError as e:
        return str(e)
