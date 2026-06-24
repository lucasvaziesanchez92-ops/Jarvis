"""LangChain tools for note management."""
from langchain_core.tools import tool

from backend.services import notes_service


@tool
def create_note(title: str, content: str, tags: list[str] | None = None) -> dict:
    """Create a new note with a title, content, and optional tags. Returns the created note.
    If a note with the same title already exists, it will be updated instead of duplicated.
    INSTRUCCIÓN: NO imprimas todo el contenido de la nota en el chat. Dile al usuario que fue creada exitosamente y dale este enlace: [Ver Nota](#wikilink:TITULO_REAL)."""
    # Check if a note with this title already exists — update instead of duplicate
    try:
        existing = notes_service.list_notes()
        for n in existing:
            if n.get("title", "").lower() == title.lower():
                return notes_service.update_note(n["id"], title, content, tags)
    except Exception:
        pass
    return notes_service.create_note(title, content, tags)


@tool
def list_notes(tag: str | None = None) -> list[dict]:
    """List all notes, optionally filtered by tag."""
    return notes_service.list_notes(tag)


@tool
def get_note(note_id: str) -> dict | None:
    """Get a specific note by its ID."""
    return notes_service.get_note(note_id)


@tool
def update_note(note_id: str = "", title: str = "", content: str | None = None, tags: list[str] | None = None) -> dict | None:
    """Update an existing note. You can find it by note_id OR by title (if you only know the title, pass it as 'title'). Use content to set new content or append to existing."""
    if not note_id and title:
        notes = notes_service.list_notes()
        for n in notes:
            if n.get("title", "").lower() == title.lower():
                note_id = n["id"]
                break
        if not note_id:
            return {"error": f"No se encontró ninguna nota con el título '{title}'."}
    if not note_id:
        return {"error": "Debes proporcionar note_id o title."}
    return notes_service.update_note(note_id, title if title else None, content, tags)


@tool
def delete_note(note_id: str = "", title: str = "") -> str:
    """Delete a note by its ID or title. If you only know the title, pass it as 'title' and the system will find the ID automatically. Returns a confirmation message."""
    if not note_id and title:
        notes = notes_service.list_notes()
        for n in notes:
            if n.get("title", "").lower() == title.lower():
                note_id = n["id"]
                break
        if not note_id:
            return f"No se encontró ninguna nota con el título '{title}'."
    if not note_id:
        return "Debes proporcionar el note_id o el title de la nota a eliminar."
    return notes_service.delete_note(note_id)
