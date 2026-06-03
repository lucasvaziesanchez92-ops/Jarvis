"""LangChain tools for note management."""
from langchain_core.tools import tool

from backend.services import notes_service


@tool
def create_note(title: str, content: str, tags: list[str] | None = None) -> dict:
    """Create a new note with a title, content, and optional tags. Returns the created note."""
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
def update_note(note_id: str, title: str | None = None, content: str | None = None, tags: list[str] | None = None) -> dict | None:
    """Update an existing note's title, content, or tags."""
    return notes_service.update_note(note_id, title, content, tags)


@tool
def delete_note(note_id: str) -> str:
    """Delete a note by its ID. Returns a confirmation message."""
    return notes_service.delete_note(note_id)
