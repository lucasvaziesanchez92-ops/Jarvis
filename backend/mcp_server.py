"""
Jarvis MCP Server — exposes all tools via the Model Context Protocol.

Run standalone (stdio transport, for Claude Desktop / LM Studio):
    python -m backend.mcp_server

Dev mode (interactive inspector):
    mcp dev backend/mcp_server.py
"""
import base64
import io
from typing import Literal
from mcp.server.fastmcp import FastMCP

from backend.services import notes_service, todos_service, calendar_service, email_service
from backend.services.backup_service import backup_notes_to_s3, backup_todos_to_s3, full_backup, list_s3_backups
from backend.services.stt_service import transcribe_audio, check_whisper_model
from backend.services.tts_service import get_tts_service, VOICE_CATALOG

mcp = FastMCP("Jarvis")


def _safe_call(fn, *args, **kwargs):
    """Wrapper that catches errors and returns user-friendly messages."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return {"error": str(e)}


# ── Notes (5 tools) ──────────────────────────────────────────────────────────

@mcp.tool()
def create_note(title: str, content: str, tags: list[str] | None = None) -> dict:
    """Create a new note with a title, content, and optional tags. Returns the created note."""
    return notes_service.create_note(title, content, tags)


@mcp.tool()
def list_notes(tag: str | None = None) -> list[dict]:
    """List all notes, optionally filtered by tag."""
    return notes_service.list_notes(tag)


@mcp.tool()
def get_note(note_id: str) -> dict | None:
    """Get a specific note by its ID."""
    return notes_service.get_note(note_id)


@mcp.tool()
def update_note(note_id: str, title: str | None = None, content: str | None = None, tags: list[str] | None = None) -> dict | None:
    """Update an existing note's title, content, or tags."""
    return notes_service.update_note(note_id, title, content, tags)


@mcp.tool()
def delete_note(note_id: str) -> str:
    """Delete a note by its ID. Returns a confirmation message."""
    return notes_service.delete_note(note_id)


# ── Todos (5 tools) ──────────────────────────────────────────────────────────

@mcp.tool()
def create_todo(text: str, priority: Literal["low", "medium", "high"] = "medium", due_date: str | None = None) -> dict:
    """Create a new to-do item. due_date should be ISO format string (e.g. 2024-12-31T10:00:00)."""
    return todos_service.create_todo(text, priority, due_date)


@mcp.tool()
def list_todos(show_completed: bool = False) -> list[dict]:
    """List to-do items. By default only shows incomplete items."""
    return todos_service.list_todos(show_completed)


@mcp.tool()
def get_todo(todo_id: str) -> dict | None:
    """Get a specific to-do by its ID."""
    return todos_service.get_todo(todo_id)


@mcp.tool()
def complete_todo(todo_id: str) -> dict | None:
    """Mark a to-do item as completed."""
    return todos_service.complete_todo(todo_id)


@mcp.tool()
def delete_todo(todo_id: str) -> str:
    """Delete a to-do item by its ID."""
    return todos_service.delete_todo(todo_id)


# ── Calendar (5 tools) ───────────────────────────────────────────────────────

@mcp.tool()
def create_calendar_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    location: str = "",
    calendar_id: str = "primary",
) -> dict:
    """Create a calendar event. Datetimes must be ISO format (e.g. 2024-12-31T10:00:00). Requires Google Calendar credentials."""
    result = _safe_call(calendar_service.create_calendar_event, title, start_datetime, end_datetime, description, location, calendar_id)
    if "error" in result:
        return result
    return result


@mcp.tool()
def list_calendar_events(upcoming_only: bool = True, calendar_id: str = "primary") -> list[dict]:
    """List calendar events. By default only shows upcoming events. Requires Google Calendar credentials."""
    result = _safe_call(calendar_service.list_calendar_events, upcoming_only, calendar_id)
    if "error" in result:
        return result
    return result


@mcp.tool()
def get_calendar_event(event_id: str, calendar_id: str = "primary") -> dict | None:
    """Get a calendar event by its ID. Requires Google Calendar credentials."""
    return _safe_call(calendar_service.get_calendar_event, event_id, calendar_id)


@mcp.tool()
def delete_calendar_event(event_id: str, calendar_id: str = "primary") -> str:
    """Delete a calendar event by its ID. Requires Google Calendar credentials."""
    return _safe_call(calendar_service.delete_calendar_event, event_id, calendar_id)


# ── Email (4 tools) ──────────────────────────────────────────────────────────

@mcp.tool()
def list_emails(max_results: int = 10, label: str = "INBOX") -> list[dict]:
    """List recent emails from a Gmail label. Returns sender, subject, snippet, and message ID. Requires Gmail credentials."""
    return _safe_call(email_service.list_emails, max_results, label)


@mcp.tool()
def get_email(message_id: str) -> dict:
    """Get the full content of an email by its message ID. Requires Gmail credentials."""
    return _safe_call(email_service.get_email, message_id)


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient. Requires Gmail credentials."""
    return _safe_call(email_service.send_email, to, subject, body)


@mcp.tool()
def search_emails(query: str, max_results: int = 10) -> list[dict]:
    """Search emails using Gmail search syntax (e.g., 'from:boss@company.com is:unread'). Requires Gmail credentials."""
    return _safe_call(email_service.search_emails, query, max_results)


# ── Search (1 tool) ──────────────────────────────────────────────────────────

@mcp.tool()
def unified_search(query: str, types: str = "all", limit: int = 20) -> dict:
    """
    Unified search across notes, todos, calendar events, and threads.
    types: comma-separated list ('notes,todos,calendar,emails') or 'all'
    Returns {query, results: [{type, id, title, content, metadata}, ...], total}
    """
    from backend.storage.sqlite_store import get_store
    from sqlalchemy import or_

    store = get_store()
    session = store.get_session()
    results = []
    type_list = types.split(",") if types != "all" else ["notes", "todos", "calendar", "emails"]

    try:
        if "notes" in type_list:
            from backend.storage.sqlite_store import NoteModel
            notes = session.query(NoteModel).filter(
                or_(NoteModel.title.ilike(f"%{query}%"), NoteModel.content.ilike(f"%{query}%"))
            ).limit(limit).all()
            for n in notes:
                results.append({"type": "note", "id": n.id, "title": n.title, "content": n.content[:200], "metadata": {"tags": n.tags}})

        if "todos" in type_list:
            from backend.storage.sqlite_store import TodoModel
            todos = session.query(TodoModel).filter(TodoModel.text.ilike(f"%{query}%")).limit(limit).all()
            for t in todos:
                results.append({"type": "todo", "id": t.id, "title": t.text, "content": f"Priority: {t.priority}, Completed: {t.completed}", "metadata": {}})

        if "emails" in type_list:
            from backend.storage.sqlite_store import ThreadModel
            threads = session.query(ThreadModel).filter(ThreadModel.title.ilike(f"%{query}%")).limit(limit).all()
            for th in threads:
                results.append({"type": "thread", "id": th.id, "title": th.title or "Untitled", "content": th.meta[:200] if th.meta else "", "metadata": {"status": th.status}})

    finally:
        session.close()

    return {"query": query, "results": results[:limit], "total": len(results)}


# ── Personas (1 tool) ───────────────────────────────────────────────────────

@mcp.tool()
def get_personas() -> list[dict]:
    """Get all available agent personas (name, label, description, icon)."""
    from backend.agent.personalities import get_all_personas
    return get_all_personas()


# ── Diagnostics (3 tools) ────────────────────────────────────────────────────

@mcp.tool()
def get_diagnostics_health() -> dict:
    """Get quick health status of the agent's memory and diagnostics system."""
    from backend.services.memory_service import memory_service
    return memory_service.get_health()


@mcp.tool()
def get_diagnostics_report() -> dict:
    """Get full diagnostic report of the agent."""
    from backend.services.memory_service import memory_service
    return memory_service.run_diagnose()


@mcp.tool()
def run_cleanup(compact_days: int = 30) -> dict:
    """Run cleanup: compact memory and clear old errors. Set compact_days to control retention."""
    from backend.services.memory_service import memory_service
    return memory_service.run_cleanup(compact_days=compact_days)


# ── STT — Speech to Text (2 tools) ───────────────────────────────────────────

@mcp.tool()
def transcribe_audio_tool(audio_base64: str, language: str = "es", task: str = "transcribe") -> dict:
    """
    Transcribe audio to text using Whisper.
    audio_base64: base64-encoded audio bytes (WAV, MP3, OGG)
    language: ISO 639-1 code (es, en, fr, de, pt, it)
    task: 'transcribe' or 'translate'
    Returns {text, language, duration, segments}
    """
    try:
        audio_bytes = base64.b64decode(audio_base64)
    except Exception as e:
        return {"error": f"Invalid base64: {e}"}

    result = _safe_call(transcribe_audio, audio_bytes, language, task)
    return result


@mcp.tool()
def get_stt_status() -> dict:
    """Check if Whisper STT is loaded and available."""
    return check_whisper_model()


# ── TTS — Text to Speech (2 tools) ───────────────────────────────────────────

@mcp.tool()
def synthesize_speech(text: str, voice_id: str = "es_ES-davefx-medium", format: str = "wav", speed: float = 1.0) -> dict:
    """
    Synthesize text to speech using Piper TTS.
    text: text to synthesize (max 5000 chars)
    voice_id: see get_tts_voices() for available options
    format: 'wav', 'mp3', or 'ogg'
    speed: 0.5 to 2.0 (1.0 is normal)
    Returns {audio_base64, format, voice_id, duration_sec}
    """
    try:
        tts = get_tts_service()
        length_scale = 2.0 - speed
        length_scale = max(0.5, min(2.0, length_scale))
        audio_bytes = tts.synthesize(text, length_scale=length_scale)
        audio_b64 = base64.b64encode(audio_bytes).decode()
        return {
            "audio_base64": audio_b64,
            "format": format,
            "voice_id": voice_id,
            "duration_sec": len(audio_bytes) / (tts.sample_rate * 2),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_tts_voices() -> dict:
    """Get list of all available Piper TTS voices."""
    voices = []
    for voice_id, info in VOICE_CATALOG.items():
        voices.append({
            "id": voice_id,
            "name": info["name"],
            "language": info["language"],
            "locale": info["locale"],
            "gender": info["gender"],
            "quality": info["quality"],
        })
    return {"voices": voices, "default_voice": "es_ES-davefx-medium"}


# ── Backup (3 tools) ─────────────────────────────────────────────────────────

@mcp.tool()
def backup_notes(backup_name: str | None = None) -> dict:
    """Backup all notes to S3. Set backup_name for a specific filename."""
    return _safe_call(backup_notes_to_s3, notes_service.list_notes(), backup_name)


@mcp.tool()
def backup_todos(backup_name: str | None = None) -> dict:
    """Backup all todos to S3. Set backup_name for a specific filename."""
    return _safe_call(backup_todos_to_s3, todos_service.list_todos(), backup_name)


@mcp.tool()
def run_full_backup() -> dict:
    """Run a complete backup of both notes and todos to S3."""
    return _safe_call(full_backup)


# ── System (2 tools) ─────────────────────────────────────────────────────────

@mcp.tool()
def get_system_health() -> dict:
    """Get overall system health: database, LLM provider, and circuit breakers status."""
    checks = {}
    try:
        from backend.storage.sqlite_store import get_store
        store = get_store()
        session = store.get_session()
        session.execute("SELECT 1")
        session.close()
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"

    try:
        from backend.llm import get_llm
        llm = get_llm()
        checks["llm_provider"] = "loaded"
    except Exception as e:
        checks["llm_provider"] = f"unavailable: {str(e)[:50]}"

    try:
        from backend.core.resilience import get_circuit_breaker_states
        checks["circuit_breakers"] = get_circuit_breaker_states()
    except Exception:
        checks["circuit_breakers"] = {}

    return {"status": "ready" if checks.get("database") == "healthy" else "degraded", "checks": checks}


@mcp.tool()
def get_backup_list(backup_type: str = "notes") -> list[dict]:
    """List available S3 backups. backup_type: 'notes' or 'todos'."""
    return list_s3_backups(backup_type)


if __name__ == "__main__":
    mcp.run()