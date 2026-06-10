"""Central tool registry — all tools available to the agent.

Tools are categorized by HARD requirement:
- CORE: always work (notes, todos, time, memory, utility). No external auth.
- GOOGLE_REQUIRED: only added to ALL_TOOLS if Google OAuth is configured.
  If Google is not configured, these tools are EXCLUDED from the LLM's
  tool list so it cannot hallucinate their execution.
- OPTIONAL: only added if their dependency (chromadb, playwright, etc.) is installed.
"""

# Notes CRUD (FULL)
from backend.tools.notes import create_note, list_notes, get_note, update_note, delete_note

# Todos CRUD (FULL)
from backend.tools.todos import create_todo, list_todos, complete_todo, update_todo, delete_todo

# Email
from backend.tools.email import search_emails, send_email, list_emails

# Wiki
from backend.tools.wiki import wiki_query, wiki_save_research, wiki_ingest

# Utility
from backend.tools.utility import get_current_time, get_current_date

# Memory
from backend.tools.memory import search_memory, save_memory, list_memories, delete_memory

# Google Suite (lazy import — requires OAuth)
try:
    from backend.tools.google_suite import (
        search_gmail, send_gmail, list_gmail,
        search_drive, list_drive_files, list_drive_folder,
        read_drive_file, get_drive_file_info,
        upload_drive_file, delete_drive_file,
        analyze_drive_image,
        list_calendar_google, create_calendar_event_google,
    )
    _GOOGLE_SUITE_IMPORTABLE = True
except Exception:
    _GOOGLE_SUITE_IMPORTABLE = False
    search_gmail = None        # type: ignore
    send_gmail = None          # type: ignore
    list_gmail = None          # type: ignore
    search_drive = None        # type: ignore
    list_drive_files = None    # type: ignore
    list_drive_folder = None   # type: ignore
    read_drive_file = None     # type: ignore
    get_drive_file_info = None # type: ignore
    upload_drive_file = None   # type: ignore
    delete_drive_file = None   # type: ignore
    analyze_drive_image = None # type: ignore
    list_calendar_google = None              # type: ignore
    create_calendar_event_google = None      # type: ignore

# Web search — lazy import (playwright may be missing).
try:
    from backend.tools.web_search import web_search
    _WEB_SEARCH_AVAILABLE = True
except Exception:
    _WEB_SEARCH_AVAILABLE = False
    web_search = None  # type: ignore

# Semantic search — DEFERRED (langchain_chroma is heavy ~150MB).
# Tools are loaded on first use, not at module import.
_SEMANTIC_AVAILABLE = False
search_notes_semantic = None   # type: ignore
search_wiki_semantic = None    # type: ignore
search_all_knowledge = None    # type: ignore
get_knowledge_stats = None     # type: ignore


def _google_oauth_configured() -> bool:
    """True only if the OAuth credentials are actually loadable. We check
    BOTH the file and the env vars, AND we verify the client_id/secret are
    not empty placeholders. This is what gates the Google tools."""
    try:
        from backend.services.google_auth import _get_client_config
        cfg = _get_client_config()
        return bool(cfg and cfg.get("client_id") and cfg.get("client_secret"))
    except Exception:
        return False


# ── Core tools (always available, no external auth) ────────────
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

# ── Google-required tools ───────────────────────────────────────
# CRITICAL: only added if Google OAuth is ACTUALLY configured. This stops
# the LLM from hallucinating Drive/Gmail/Calendar executions when there
# are no credentials — it simply won't see those tools in its schema.
_GOOGLE_TOOLS = []
if _GOOGLE_SUITE_IMPORTABLE and _google_oauth_configured():
    _GOOGLE_TOOLS = [
        list_gmail, search_gmail, send_gmail,
        search_drive, list_drive_files, list_drive_folder,
        read_drive_file, get_drive_file_info,
        upload_drive_file, delete_drive_file,
        analyze_drive_image,
        list_calendar_google, create_calendar_event_google,
    ]

# ── Extended tools — email (legacy) + memory ───────────────────
EXTENDED_TOOLS = [
    search_emails, send_email, list_emails,
    search_memory, save_memory, list_memories, delete_memory,
]

# ── All tools combined, filtered clean ──────────────────────────
ALL_TOOLS = [t for t in CORE_TOOLS + _GOOGLE_TOOLS + EXTENDED_TOOLS if t is not None]


def get_tool_status() -> dict:
    """Diagnostic: which tools are available right now and why.
    Returns a dict with categories and which tool names are in each.
    Used by /api/v1/diagnostics/tools so the operator can see at a glance
    which integrations are live."""
    return {
        "google_oauth_configured": _google_oauth_configured(),
        "google_suite_importable": _GOOGLE_SUITE_IMPORTABLE,
        "web_search_available": _WEB_SEARCH_AVAILABLE and web_search is not None,
        "semantic_search_available": _SEMANTIC_AVAILABLE,
        "core_tools": [t.name for t in CORE_TOOLS],
        "google_tools": [t.name for t in _GOOGLE_TOOLS],
        "extended_tools": [t.name for t in EXTENDED_TOOLS],
        "all_tools": [t.name for t in ALL_TOOLS],
        "total": len(ALL_TOOLS),
    }
