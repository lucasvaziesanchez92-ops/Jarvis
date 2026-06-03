"""Central tool registry — all tools available to the agent."""

# Notes CRUD (FULL)
from backend.tools.notes import create_note, list_notes, get_note, update_note, delete_note

# Todos CRUD (FULL)
from backend.tools.todos import create_todo, list_todos, complete_todo, update_todo, delete_todo

# Calendar
from backend.tools.calendar import list_calendar_events, create_calendar_event, update_calendar_event, delete_calendar_event

# Email
from backend.tools.email import search_emails, send_email, list_emails

# Wiki
from backend.tools.wiki import wiki_query, wiki_save_research, wiki_ingest

# Utility
from backend.tools.utility import get_current_time, get_current_date

# Memory (now wired)
from backend.tools.memory import search_memory, save_memory, list_memories, delete_memory

# Google Suite (lazy import — requires OAuth)
try:
    from backend.tools.google_suite import (
        search_gmail, send_gmail, list_gmail,
        search_drive, list_drive_files,
        list_calendar_google, create_calendar_event_google,
    )
    _GOOGLE_SUITE_AVAILABLE = True
except Exception:
    _GOOGLE_SUITE_AVAILABLE = False
    search_gmail = None        # type: ignore
    send_gmail = None          # type: ignore
    list_gmail = None          # type: ignore
    search_drive = None        # type: ignore
    list_drive_files = None    # type: ignore
    list_calendar_google = None              # type: ignore
    create_calendar_event_google = None      # type: ignore

# Web search — lazy import (playwright may be missing).
try:
    from backend.tools.web_search import web_search
    _WEB_SEARCH_AVAILABLE = True
except Exception:
    _WEB_SEARCH_AVAILABLE = False
    web_search = None  # type: ignore

# Semantic search — lazy import (langchain_chroma may be missing).
try:
    from backend.tools.semantic_search import (
        search_notes_semantic,
        search_wiki_semantic,
        search_all_knowledge,
        get_knowledge_stats,
    )
    _SEMANTIC_AVAILABLE = True
except Exception:
    _SEMANTIC_AVAILABLE = False
    search_notes_semantic = None   # type: ignore
    search_wiki_semantic = None    # type: ignore
    search_all_knowledge = None    # type: ignore
    get_knowledge_stats = None     # type: ignore

# ── Core tools (always available) ──────────────────────────────
CORE_TOOLS = [
    # Notes (full CRUD)
    create_note, list_notes, get_note, update_note, delete_note,
    # Todos (full CRUD)
    create_todo, list_todos, complete_todo, update_todo, delete_todo,
    # Wiki
    wiki_query, wiki_save_research, wiki_ingest,
    # Time
    get_current_time, get_current_date,
]

# Web search (if playwright installed)
if _WEB_SEARCH_AVAILABLE and web_search is not None:
    CORE_TOOLS.append(web_search)

# Semantic search (if chromadb installed)
if _SEMANTIC_AVAILABLE:
    CORE_TOOLS += [
        search_notes_semantic,
        search_wiki_semantic,
        search_all_knowledge,
        get_knowledge_stats,
    ]

# Google Suite — unified (replaces old email/calendar tools)
if _GOOGLE_SUITE_AVAILABLE:
    CORE_TOOLS += [
        list_gmail, search_gmail, send_gmail,
        search_drive, list_drive_files,
        list_calendar_google, create_calendar_event_google,
    ]

# ── Extended tools — calendar + email (legacy, kept for compatibility) ──
EXTENDED_TOOLS = [
    list_calendar_events, create_calendar_event, update_calendar_event, delete_calendar_event,
    search_emails, send_email, list_emails,
    search_memory, save_memory, list_memories, delete_memory,
]

# ── All tools combined, filtered clean ──────────────────────────
ALL_TOOLS = [t for t in CORE_TOOLS + EXTENDED_TOOLS if t is not None]
