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
    """Search files in Google Drive. Args: query keywords."""
    from backend.services.drive_service import list_files
    try:
        results = list_files(query=query, max_results=20)
        if not results:
            return "No se encontraron archivos en Drive."
        lines = [f"{len(results)} archivos encontrados:"]
        for f in results:
            lines.append(f"- {f['name']} ({f.get('size', 'N/A')} bytes) ID:{f['id']}")
        return "\n".join(lines)
    except RuntimeError as e:
        return str(e)

@tool
def list_drive_files() -> str:
    """List recent files from Google Drive."""
    from backend.services.drive_service import list_files
    try:
        results = list_files(max_results=20)
        if not results:
            return "No hay archivos en Drive."
        lines = [f"{len(results)} archivos en Drive:"]
        for f in results:
            lines.append(f"- {f['name']} ({f.get('size', 'N/A')} bytes)")
        return "\n".join(lines)
    except RuntimeError as e:
        return str(e)

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
def create_calendar_event_google(summary: str, start_time: str, end_time: str) -> str:
    """Create a Google Calendar event. Args: summary, start_time (ISO 8601), end_time (ISO 8601)."""
    from backend.services.calendar_service import create_event
    try:
        result = create_event(summary, start_time, end_time)
        return f"Evento creado: {result['summary']} ({result['id']})"
    except RuntimeError as e:
        return str(e)
