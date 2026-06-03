# PRD 2: Jarvis Backend (FastAPI + LangGraph + MCP)

> **Technology Stack**: Python FastAPI + LangGraph + SQLAlchemy + MCP  
> **Base Directory**: `backend/`  
> **Status**: Phase 3 — Core architecture complete, needs enhancement  
> **Server**: `uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000`

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Current State Analysis](#2-current-state-analysis)
3. [Backend Layer Specifications](#3-backend-layer-specifications)
4. [API Endpoints](#4-api-endpoints)
5. [Agent Layer (LangGraph)](#5-agent-layer-langgraph)
6. [Tool Layer](#6-tool-layer)
7. [LLM Provider Layer](#7-llm-provider-layer)
8. [MCP Server](#8-mcp-server)
9. [Storage Layer](#9-storage-layer)
10. [Services Layer](#10-services-layer)
11. [Monitoring & Observability](#11-monitoring--observability)
12. [Task Management System](#12-task-management-system)
13. [Authentication & Security](#13-authentication--security)
14. [Implementation Roadmap](#14-implementation-roadmap)

---

## 1. Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Clients                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Mobile (Expo)│  │  Web (Future)│  │ Claude Desktop    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
└─────────┼─────────────────┼───────────────────┼────────────┘
          │                 │                   │
     REST / WS         REST / WS            MCP (stdio)
          │                 │                   │
┌─────────┴─────────────────┴───────────────────┴────────────┐
│                    FastAPI Application                       │
├────────────────────────────────────────────────────────────┤
│  Routers:                                                    │
│  ├── chat.py       → POST /chat, WS /ws/chat               │
│  ├── notes.py      → CRUD /notes                           │
│  ├── todos.py      → CRUD /todos                           │
│  ├── calendar.py   → CRUD /calendar                        │
│  ├── email.py      → CRUD /emails                          │
│  ├── threads.py    → CRUD /threads                         │
│  └── messages.py   → CRUD /messages                        │
├────────────────────────────────────────────────────────────┤
│  Dependency Injection:                                       │
│  └── dependencies.py → get_jarvis_graph()                   │
├────────────────────────────────────────────────────────────┤
│  LangGraph Agent (StateGraph):                               │
│  ├── state.py    → JarvisState(MessagesState)               │
│  ├── graph.py    → START → agent ↔ tools → END             │
│  ├── nodes.py    → call_model, call_model_with_tools        │
│  └── prompts.py  → SYSTEM_PROMPT                            │
├────────────────────────────────────────────────────────────┤
│  LLM Provider Factory (backend/llm/__init__.py):             │
│  ├── ollama.py   → ChatOllama (local)                       │
│  └── bedrock.py  → ChatBedrockConverse (cloud)              │
├────────────────────────────────────────────────────────────┤
│  Tool Registry (backend/tools/registry.py):                  │
│  ├── notes.py    → 5 tools (create, list, get, update, del) │
│  ├── todos.py    → 4 tools (create, list, complete, del)    │
│  ├── calendar.py → 5 tools (CRUD events)                    │
│  └── email.py    → 4 tools (list, get, send, search)        │
│  Total: 18 tools                                             │
├────────────────────────────────────────────────────────────┤
│  MCP Server (backend/mcp_server.py):                         │
│  └── FastMCP exposing same 18 tools via stdio               │
├────────────────────────────────────────────────────────────┤
│  Services Layer (backend/services/):                         │
│  ├── notes_service.py     → SQLite Note CRUD               │
│  ├── todos_service.py     → SQLite Todo CRUD               │
│  ├── calendar_service.py  → Google Calendar API             │
│  ├── email_service.py     → Gmail API                       │
│  ├── messages_service.py  → Thread messages                 │
│  └── threads_service.py   → Conversation threads            │
├────────────────────────────────────────────────────────────┤
│  Storage Layer (backend/storage/):                           │
│  └── sqlite_store.py → SQLAlchemy SQLite with models:       │
│      ├── NoteModel     → notes table                       │
│      ├── TodoModel     → todos table                        │
│      ├── ThreadModel   → threads table                      │
│      └── MessageModel  → messages table                     │
└────────────────────────────────────────────────────────────┘
```

### Key Files Map

| Layer | File | Absolute Path | Purpose |
|-------|------|--------------|---------|
| Config | `config.py` | `backend/config.py` | Pydantic-settings reads `.env` |
| App | `main.py` | `backend/api/main.py` | FastAPI app, CORS, router mounting, lifespan |
| Dependencies | `dependencies.py` | `backend/api/dependencies.py` | get_jarvis_graph() singleton |
| Chat Router | `chat.py` | `backend/api/routers/chat.py` | POST /chat + WS /ws/chat |
| Agent State | `state.py` | `backend/agent/state.py` | JarvisState(MessagesState) |
| Agent Graph | `graph.py` | `backend/agent/graph.py` | build_graph(), get_graph() |
| Agent Nodes | `nodes.py` | `backend/agent/nodes.py` | call_model, call_model_with_tools |
| Agent Prompts | `prompts.py` | `backend/agent/prompts.py` | SYSTEM_PROMPT |
| LLM Factory | `__init__.py` | `backend/llm/__init__.py` | get_llm() provider router |
| LLM Ollama | `ollama.py` | `backend/llm/ollama.py` | ChatOllama factory |
| LLM Bedrock | `bedrock.py` | `backend/llm/bedrock.py` | ChatBedrockConverse factory |
| Tool Registry | `registry.py` | `backend/tools/registry.py` | ALL_TOOLS list |
| MCP Server | `mcp_server.py` | `backend/mcp_server.py` | FastMCP with 18 tools |
| SQLite Store | `sqlite_store.py` | `backend/storage/sqlite_store.py` | SqliteStore, SQLAlchemy models |

---

## 2. Current State Analysis

### What Works Well

- **Clean Layered Architecture**: Config → LLM → Agent → Tools → Services → Storage
- **LangGraph StateGraph**: Proper ReAct pattern with `tools_condition` routing
- **Tool Registry Pattern**: Single `ALL_TOOLS` list — add a tool, register it once
- **MCP Server**: Exposes same tools via Model Context Protocol for Claude Desktop
- **Provider Toggle**: `llm_provider` setting in `.env` switches between Ollama and Bedrock
- **WebSocket Streaming**: `astream_events` for real-time token/tool streaming
- **SQLite Persistence**: SQLAlchemy with proper session management

### What Needs Improvement

1. **No Conversation Persistence**: Messages are lost between server restarts
2. **No Checkpointing**: LangGraph graph state is not saved between turns
3. **No Web Search Tool**: Cannot fetch real-time information
4. **No Token/Memory Management**: No conversation summarization or context window management
5. **No Rate Limiting**: API endpoints have no throttling
6. **No Authentication**: All endpoints are open
7. **No Pagination**: List endpoints return all records
8. **No Observability**: No request logging, tool metrics, or LangSmith integration
9. **Graph Singleton**: `_graph` singleton doesn't support per-session state
10. **No Scheduled Tasks**: No cron-like scheduling for recurring operations

---

## 3. Backend Layer Specifications

### 3.1 Configuration Layer

**File**: `backend/config.py`

**Current Settings**:
```python
class Settings(BaseSettings):
    # AWS / Bedrock
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-5"
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    
    # Provider toggle
    llm_provider: str = "ollama"  # "bedrock" or "ollama"
    
    # Storage
    data_dir: str = "data"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["*"]
```

**Enhancements to Add**:

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `lm_studio_base_url` | str | `http://localhost:1234/v1` | LM Studio OpenAI-compatible endpoint |
| `llm_provider` options | enum | `ollama\|bedrock\|lm_studio` | Add third provider option |
| `max_context_messages` | int | `50` | Window size for conversation memory |
| `enable_langsmith` | bool | `false` | Toggle LangSmith observability |
| `langsmith_api_key` | str | `""` | LangSmith API key |
| `rate_limit_per_minute` | int | `60` | API rate limiting |
| `api_secret_key` | str | `""` | API authentication key |
| `enable_cors_credentials` | bool | `false` | CORS credentials flag |
| `tavily_api_key` | str | `""` | Web search API key |
| `conversation_memory_type` | enum | `window\|summary\|vector` | Memory strategy |

### 3.2 FastAPI Application Layer

**File**: `backend/api/main.py`

**Current Structure**:
- Lifespan event pre-warms the LangGraph graph
- CORS middleware configured from settings
- 7 routers mounted (chat, notes, todos, calendar, emails, threads, messages)
- Health endpoint at `GET /health`

**Enhancements to Add**:

| Feature | Implementation | Priority |
|---------|---------------|----------|
| Rate Limiting | `slowapi` middleware with per-IP tracking | High |
| API Key Auth | `Depends()` function checking `X-API-Key` header | High |
| Request Logging | Middleware logging method, path, duration, status | High |
| Pagination | Query params `?skip=0&limit=20` on list endpoints | High |
| Error Handler | Custom exception handlers with structured JSON responses | High |
| API Versioning | Prefix `/api/v1/` for future breaking changes | Medium |
| OpenAPI Tags | Organize Swagger docs by domain | Low |

---

## 4. API Endpoints

### 4.1 Current Endpoints

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| `GET` | `/health` | `health()` | Service health check |
| `POST` | `/chat` | `chat()` | Blocking chat invocation |
| `WS` | `/ws/chat` | `ws_chat()` | Streaming chat via WebSocket |
| `GET` | `/notes` | `list_notes()` | List all notes |
| `POST` | `/notes` | `create_note()` | Create a note |
| `GET` | `/notes/{id}` | `get_note()` | Get note by ID |
| `PUT` | `/notes/{id}` | `update_note()` | Update note |
| `DELETE` | `/notes/{id}` | `delete_note()` | Delete note |
| `GET` | `/todos` | `list_todos()` | List todos |
| `POST` | `/todos` | `create_todo()` | Create todo |
| `GET` | `/todos/{id}` | `get_todo()` | Get todo by ID |
| `PATCH` | `/todos/{id}/complete` | `complete_todo()` | Mark todo complete |
| `DELETE` | `/todos/{id}` | `delete_todo()` | Delete todo |
| `GET` | `/calendar` | `list_events()` | List calendar events |
| `POST` | `/calendar` | `create_event()` | Create calendar event |
| `GET` | `/calendar/{id}` | `get_event()` | Get event by ID |
| `PUT` | `/calendar/{id}` | `update_event()` | Update event |
| `DELETE` | `/calendar/{id}` | `delete_event()` | Delete event |
| `GET` | `/emails` | `list_emails()` | List recent emails |
| `GET` | `/emails/{message_id}` | `get_email()` | Get full email content |
| `GET` | `/emails/search` | `search_emails()` | Search emails |
| `POST` | `/emails/send` | `send_email()` | Send email |
| `GET` | `/threads` | `list_threads()` | List conversation threads |
| `POST` | `/threads` | `create_thread()` | Create new thread |
| `GET` | `/threads/{id}` | `get_thread()` | Get thread details |
| `GET` | `/threads/{id}/messages` | `list_messages()` | List messages in thread |

### 4.2 Endpoints to Add

| Method | Path | Description | Priority |
|--------|------|-------------|----------|
| `POST` | `/chat/stream` | Server-Sent Events streaming (alternative to WS) | High |
| `GET` | `/threads/{id}/history` | Get full conversation history with pagination | High |
| `DELETE` | `/threads/{id}` | Delete thread and all messages | High |
| `GET` | `/search` | Unified search across all domains | High |
| `GET` | `/metrics` | Prometheus-style metrics endpoint | Medium |
| `POST` | `/settings` | Update runtime settings | Medium |
| `GET` | `/settings` | Get current settings (sanitized) | Medium |
| `POST` | `/todos/{id}` | Full update todo (PUT) | Medium |
| `GET` | `/todos/upcoming` | Todos due in next N days | Medium |
| `GET` | `/calendar/today` | Today's events only | Medium |
| `POST` | `/emails/{id}/reply` | Reply to email | Low |

### 4.3 Pagination Pattern

All list endpoints should support:

```python
# Query parameters
skip: int = Query(0, ge=0)        # Offset
limit: int = Query(20, ge=1, le=100)  # Page size
```

Response format:
```python
class PaginatedResponse(BaseModel):
    items: list[T]
    total: int
    skip: int
    limit: int
    has_more: bool
```

---

## 5. Agent Layer (LangGraph)

### 5.1 Current Architecture

**File**: `backend/agent/graph.py`

```
Phase 1 (no tools):  START → agent → END
Phase 2+ (tools):    START → agent ↔ tools → END
```

**Graph Flow with Tools**:
```
START
  │
  ▼
┌─────────────┐
│   agent     │  ← LLM decides: respond or call tool?
└──────┬──────┘
       │
  tools_condition()
   ╱         ╲
  ▼           ▼
END      ┌─────────┐
         │  tools   │  ← Execute tool(s)
         └────┬─────┘
              │
              ▼
         back to agent (with tool results)
```

### 5.2 Enhancements Needed

| Enhancement | Description | File | Priority |
|-------------|-------------|------|----------|
| **Checkpoint Persistence** | Save graph state between turns for conversation recovery | `graph.py` | High |
| **Per-Session State** | Separate state per session_id instead of global singleton | `graph.py` | High |
| **Intent Classification** | Route queries to specialized tool groups | New `nodes.py` node | High |
| **Memory Management** | Summarize old messages when context window fills | New `nodes.py` node | High |
| **Human-in-the-Loop** | Require confirmation before destructive actions | `graph.py` conditional edge | Medium |
| **Planning Node** | Break complex tasks into sub-steps | New `nodes.py` node | Medium |
| **Fallback LLM** | Switch to backup LLM if primary fails | `llm/__init__.py` | Medium |

### 5.3 Checkpoint Persistence

**Implementation Pattern** (LangGraph `checkpointer`):

```python
from langgraph.checkpoint.memory import MemorySaver
# Or for persistence across restarts:
from langgraph.checkpoint.sqlite import SqliteSaver

# In graph.py build_graph():
checkpointer = SqliteSaver.from_conn_string("file:checkpoints.db")
graph = builder.compile(checkpointer=checkpointer)

# Thread-based config for per-session state:
config = {"configurable": {"thread_id": session_id}}
state = await graph.ainvoke(messages, config=config)
```

### 5.4 Intent Classification Node

**Purpose**: Classify user intent and route to appropriate tool subset.

```python
# In nodes.py:
def classify_intent(state: JarvisState) -> dict:
    """Determine which tool domain the user's request targets."""
    # Use lightweight LLM call or rule-based classification
    # Returns: {"intent": "notes"|"todos"|"calendar"|"email"|"general"}
    ...

# In graph.py:
builder.add_node("classifier", classify_intent)
builder.add_edge(START, "classifier")
builder.add_conditional_edges("classifier", route_by_intent)
```

### 5.5 Memory Management

**ConversationWindow Memory**:
```python
# Keep last N messages, summarize older ones
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

def trim_messages(state: JarvisState, max_messages: int = 50) -> dict:
    """Trim message history to fit context window."""
    messages = state["messages"]
    if len(messages) <= max_messages:
        return {}
    
    # Keep system prompt + recent messages
    system_msg = messages[0] if isinstance(messages[0], SystemMessage) else None
    recent = messages[-max_messages:]
    
    trimmed = [system_msg] + recent if system_msg else recent
    return {"messages": trimmed}
```

### 5.6 Updated System Prompt

**File**: `backend/agent/prompts.py`

Current prompt is good but should be enhanced with:

```python
SYSTEM_PROMPT = """You are Jarvis, a highly capable personal assistant. You are concise, \
helpful, and proactive.

## Capabilities
- Taking and managing notes (create, list, get, update, delete)
- Managing to-do lists and tasks (create, list, complete, delete with priorities and due dates)
- Scheduling and reviewing calendar events (create, list, get, update, delete)
- Reading, searching, and sending emails (list, get, search, send via Gmail)

## Tool Usage Rules
- Use tools only when the user's request requires them
- Always verify tool results before responding to the user
- If a tool call fails, explain the error clearly and suggest alternatives
- If information is missing, ask a brief clarifying question
- Never invent data; respond "I don't have that information" if tools return nothing

## Response Format
- Confirm when you create, update, or delete something
- When listing items, format them clearly
- For todos, use checkbox format:
  - [ ] Task text (priority: medium, due: 2024-12-31)
  - [x] Completed task

## Web Search
- Use web search when the user asks about current events or real-time information
- Use web search for facts that may have changed since your training cutoff

## Safety
- Ask for confirmation before deleting or sending anything
- Never expose raw tool output that contains sensitive information
"""
```

---

## 6. Tool Layer

### 6.1 Current Tools (18 total)

| Domain | File | Tools | Count |
|--------|------|-------|-------|
| Notes | `backend/tools/notes.py` | create_note, list_notes, get_note, update_note, delete_note | 5 |
| Todos | `backend/tools/todos.py` | create_todo, list_todos, complete_todo, delete_todo | 4 |
| Calendar | `backend/tools/calendar.py` | create_calendar_event, list_calendar_events, get_calendar_event, update_calendar_event, delete_calendar_event | 5 |
| Email | `backend/tools/email.py` | list_emails, get_email, send_email, search_emails | 4 |

### 6.2 Tools to Add

| Tool | Domain | Description | Priority |
|------|--------|-------------|----------|
| `web_search` | Search | Tavily or DuckDuckGo for real-time info | High |
| `get_current_time` | System | Return current date/time for time-aware queries | High |
| `file_read` | Files | Read local files (CSV, text, JSON) | Medium |
| `file_write` | Files | Write data to local files | Medium |
| `code_execute` | Code | Execute Python/JS code snippets | Medium |
| `system_info` | System | Get system info (disk, memory, uptime) | Low |
| `get_weather` | Weather | Weather lookup for a location | Low |
| `send_notification` | System | Send push notification to mobile | Low |

### 6.3 Tool Implementation Pattern

**Example: Adding Web Search**

```python
# backend/tools/web_search.py
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from backend.config import settings

@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for current information. Use when you need up-to-date facts."""
    try:
        search = TavilySearch(max_results=max_results)
        results = search.run(query)
        return results
    except Exception as e:
        return f"Error performing web search: {str(e)}"
```

**Register in `backend/tools/registry.py`**:
```python
from backend.tools.web_search import web_search

ALL_TOOLS = [
    # ... existing tools ...
    web_search,  # NEW
]
```

### 6.4 Tool Error Handling Pattern

```python
from langchain_core.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential

@tool
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def create_calendar_event(title: str, start_datetime: str, ...) -> dict:
    """Create a calendar event."""
    try:
        return calendar_service.create_calendar_event(title, start_datetime, ...)
    except ConnectionError:
        return {"error": "Cannot connect to Google Calendar. Please check your connection."}
    except PermissionError:
        return {"error": "Calendar permission denied. Please re-authenticate."}
    except Exception as e:
        return {"error": f"Failed to create event: {str(e)}"}
```

---

## 7. LLM Provider Layer

### 7.1 Current Architecture

**File**: `backend/llm/__init__.py`

```python
def get_llm() -> BaseChatModel:
    if settings.llm_provider == "ollama":
        from backend.llm.ollama import get_llm
        return get_ollama_llm()
    elif settings.llm_provider == "bedrock":
        from backend.llm.bedrock import get_llm
        return get_bedrock_llm()
```

### 7.2 Add LM Studio Support

**New File**: `backend/llm/lm_studio.py`

```python
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from backend.config import settings

def get_llm() -> BaseChatModel:
    """Return a ChatOpenAI instance pointing to LM Studio."""
    return ChatOpenAI(
        model="local-model",  # LM Studio model name
        openai_api_key="not-needed",  # LM Studio doesn't need a key
        openai_api_base=f"{settings.lm_studio_base_url}",  # e.g., http://localhost:1234/v1
        temperature=0.2,
        max_tokens=4096,
    )
```

**Update Factory**: `backend/llm/__init__.py`

```python
def get_llm() -> BaseChatModel:
    if settings.llm_provider == "ollama":
        from backend.llm.ollama import get_llm as get_ollama_llm
        return get_ollama_llm()
    elif settings.llm_provider == "bedrock":
        from backend.llm.bedrock import get_llm as get_bedrock_llm
        return get_bedrock_llm()
    elif settings.llm_provider == "lm_studio":
        from backend.llm.lm_studio import get_llm as get_lm_studio_llm
        return get_lm_studio_llm()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

### 7.3 LLM Configuration Options

| Provider | Config File | Environment Variables | Best For |
|----------|-------------|----------------------|----------|
| Ollama | `backend/llm/ollama.py` | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Local, private, no API costs |
| Bedrock | `backend/llm/bedrock.py` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `BEDROCK_MODEL_ID` | Production quality |
| LM Studio | `backend/llm/lm_studio.py` | `LM_STUDIO_BASE_URL` | Local with OpenAI-compatible API |

### 7.4 LLM Fallback Pattern

```python
def get_llm_with_fallback(primary_provider: str | None = None) -> BaseChatModel:
    """Get primary LLM with automatic fallback."""
    provider = primary_provider or settings.llm_provider
    
    try:
        return get_llm_for_provider(provider)
    except Exception as e:
        logger.warning(f"Primary LLM provider '{provider}' failed: {e}. Falling back to ollama.")
        fallback = "ollama" if provider != "ollama" else "bedrock"
        return get_llm_for_provider(fallback)
```

---

## 8. MCP Server

### 8.1 Current State

**File**: `backend/mcp_server.py`

- Uses `FastMCP` from `mcp.server.fastmcp`
- Exposes all 18 tools (notes, todos, calendar, email)
- Runs via stdio transport (`mcp.run()`)
- Can be run standalone: `python -m backend.mcp_server`
- Can be used with Claude Desktop inspector: `mcp dev backend/mcp_server.py`

### 8.2 MCP Architecture

```
┌──────────────────┐
│  Claude Desktop   │
│  or MCP Client    │
└────────┬─────────┘
         │ stdio / SSE
         ▼
┌──────────────────┐
│  FastMCP Server   │
│  (mcp_server.py)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Service Layer    │
│  (notes, todos,   │
│   calendar, email)│
└──────────────────┘
```

### 8.3 MCP Enhancements

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| SSE Transport | Add HTTP SSE endpoint for web clients | Medium |
| Multi-Server | Connect to additional MCP servers (e.g., filesystem, database) | Medium |
| Tool Metadata | Add descriptions, examples, and usage hints to tools | Low |
| Authentication | Add auth layer for MCP tool calls | Medium |

---

## 9. Storage Layer

### 9.1 Current State

**File**: `backend/storage/sqlite_store.py`

- SQLAlchemy with SQLite
- Models: NoteModel, TodoModel, ThreadModel, MessageModel
- Single global instance (`_store = SqliteStore()`)
- Database file: `data/jarvis.db`

### 9.2 Enhancements Needed

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| **Conversation History Persistence** | Save LangGraph conversation state to DB | High |
| **Vector Store** | Add ChromaDB or FAISS for semantic search/memory | High |
| **Checkpoint Store** | SQLite-backed LangGraph checkpointing | High |
| **Connection Pooling** | Configure pool_size and max_overflow | Medium |
| **Async Support** | Use `create_async_engine` for async FastAPI | Medium |
| **Migration System** | Alembic for schema migrations | Medium |

### 9.3 Vector Store Integration (for Memory/RAG)

```python
# backend/storage/vector_store.py
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from backend.config import settings

def get_vector_store():
    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=settings.ollama_base_url,
    )
    return Chroma(
        persist_directory=str(Path(settings.data_dir) / "chroma_db"),
        embedding_function=embeddings,
    )
```

**Use Cases**:
- Semantic search across notes, todos, emails
- Long-term memory retrieval for the agent
- RAG (Retrieval-Augmented Generation) for context-aware responses

---

## 10. Services Layer

### 10.1 Current Services

| Service | File | Dependencies | Status |
|---------|------|-------------|--------|
| Notes | `services/notes_service.py` | SQLAlchemy | ✅ Complete |
| Todos | `services/todos_service.py` | SQLAlchemy | ✅ Complete |
| Calendar | `services/calendar_service.py` | Google Calendar API | ✅ Complete (needs OAuth) |
| Email | `services/email_service.py` | Gmail API | ✅ Complete (needs OAuth) |
| Messages | `services/messages_service.py` | SQLAlchemy | ✅ Complete |
| Threads | `services/threads_service.py` | SQLAlchemy | ✅ Complete |

### 10.2 Service Enhancement Patterns

**Circuit Breaker for External APIs**:
```python
from pybreaker import CircuitBreaker

calendar_breaker = CircuitBreaker(
    fail_max=5,       # Open circuit after 5 failures
    recovery_timeout=60,  # Retry after 60 seconds
)

@calendar_breaker
def create_calendar_event(...):
    return google_calendar.events().insert(...)
```

**Retry with Exponential Backoff**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    reraise=True,
)
def send_email(to: str, subject: str, body: str) -> str:
    return gmail_service.send(...)
```

---

## 11. Monitoring & Observability

### 11.1 Current State

No monitoring or observability exists. No request logging, no metrics, no tracing.

### 11.2 Monitoring Stack

| Component | Tool | Purpose | Implementation |
|-----------|------|---------|----------------|
| Request Logging | FastAPI Middleware | Log every request/response | `backend/api/middleware/logging.py` |
| LangSmith | LangChain's platform | Trace LLM calls, tool usage, latency | `.env` + `langsmith` package |
| Prometheus Metrics | `prometheus-fastapi-instrumentator` | HTTP metrics (latency, error rate) | `backend/api/main.py` |
| Health Checks | `GET /health` + `GET /metrics` | Service status | New endpoint |
| Structured Logging | `structlog` | JSON-formatted logs | Replace print statements |

### 11.3 LangSmith Integration

**Environment Variables** (`.env`):
```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=jarvis
```

**Code** (`backend/api/main.py` lifespan):
```python
import os
from langsmith import Client

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.enable_langsmith:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = "jarvis"
    
    get_jarvis_graph()
    yield
```

### 11.4 Request Logging Middleware

**New File**: `backend/api/middleware/logging.py`

```python
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("jarvis.requests")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        
        logger.info(
            "%s %s %d %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration * 1000,
        )
        return response
```

### 11.5 Metrics Endpoint

**New Endpoint**: `GET /metrics`

```python
from prometheus_fastapi_instrumentator import Instrumentator

# In main.py:
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

Returns Prometheus metrics:
- `http_requests_total` — total requests by path/method/status
- `http_request_duration_seconds` — request latency histogram
- `http_requests_in_progress` — concurrent requests

---

## 12. Task Management System

### 12.1 Current State

No scheduled task system exists. All operations are request-driven (no background jobs).

### 12.2 Planned Task System

**Architecture**:
```
┌─────────────────────────────────┐
│       Task Scheduler            │
│  (APScheduler or Celery)        │
├─────────────────────────────────┤
│  Task Types:                     │
│  ├── Recurring todos (daily)     │
│  ├── Calendar reminders          │
│  ├── Email digest summaries      │
│  ├── Note cleanup/archival       │
│  └── Memory summarization        │
├─────────────────────────────────┤
│  Storage:                        │
│  └── SQLite job store            │
└─────────────────────────────────┘
```

### 12.3 Implementation with APScheduler

**New File**: `backend/scheduler/__init__.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from backend.storage.sqlite_store import get_store

scheduler = AsyncIOScheduler()

def init_scheduler():
    store = get_store()
    jobstore = SQLAlchemyJobStore(engine=store.engine)
    scheduler.add_jobstore(jobstore, alias="default")
    
    # Daily recurring tasks
    scheduler.add_job(
        generate_daily_summary,
        "cron",
        hour=8,  # 8 AM daily
        id="daily_summary",
        replace_existing=True,
    )
    
    scheduler.add_job(
        check_overdue_todos,
        "cron",
        hour=0,  # Midnight
        id="check_overdue",
        replace_existing=True,
    )
    
    scheduler.start()
```

### 12.4 Task Types

| Task | Schedule | Description | Output |
|------|----------|-------------|--------|
| Daily Summary | 8:00 AM | Generate summary of today's tasks, events, emails | Note created |
| Overdue Check | Midnight | Mark todos past due date as overdue | Todo updates |
| Memory Cleanup | 3:00 AM | Summarize old conversation history | Compressed messages |
| Email Digest | 6:00 PM | Summarize important emails received today | Note created |
| Calendar Prep | 7:00 AM | Create prep notes for today's meetings | Note created |

---

## 13. Authentication & Security

### 13.1 Current State

No authentication. All endpoints are publicly accessible.

### 13.2 Authentication Strategy

**Approach**: API Key Authentication (simple, works for personal assistant)

**Implementation**:

**New File**: `backend/api/security.py`

```python
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from backend.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not settings.api_secret_key:
        return  # Auth disabled in dev mode
    
    if api_key != settings.api_secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
```

**Apply to routers**:
```python
# In each router:
from backend.api.security import verify_api_key

router = APIRouter(dependencies=[Depends(verify_api_key)])
```

### 13.3 Security Checklist

| Item | Status | Notes |
|------|--------|-------|
| API Key Auth | ❌ Not implemented | Use `X-API-Key` header |
| CORS Restriction | ⚠️ Wildcard `*` | Restrict to known origins |
| Rate Limiting | ❌ Not implemented | Use `slowapi` |
| Input Validation | ✅ Pydantic models | Already in place |
| SQL Injection | ✅ SQLAlchemy ORM | Parameterized queries |
| Secrets in `.env` | ✅ Pydantic-settings | Never commit `.env` |
| HTTPS | ❌ Not enforced | Use reverse proxy (nginx/caddy) |
| Google OAuth Tokens | ✅ File-based storage | Encrypt token files |

---

## 14. Implementation Roadmap

### Phase 3.1: Core Enhancements (High Priority)

| Task | Files Affected | Effort |
|------|---------------|--------|
| LM Studio LLM provider | New `backend/llm/lm_studio.py`, update `__init__.py` | Small |
| Web Search tool | New `backend/tools/web_search.py`, update `registry.py` | Small |
| Conversation checkpoint persistence | Update `backend/agent/graph.py` | Medium |
| Per-session graph state | Update `dependencies.py`, `graph.py` | Medium |
| Request logging middleware | New `backend/api/middleware/logging.py` | Small |
| Pagination on list endpoints | Update all routers | Medium |
| API Key authentication | New `backend/api/security.py` | Small |
| LangSmith integration | `.env` + `main.py` lifespan | Small |

### Phase 3.2: Features (Medium Priority)

| Task | Files Affected | Effort |
|------|---------------|--------|
| Task scheduler (APScheduler) | New `backend/scheduler/` | Large |
| Vector store for semantic memory | New `backend/storage/vector_store.py` | Medium |
| Intent classification node | New `nodes.py` node, update `graph.py` | Medium |
| Memory management (trim/summarize) | New `nodes.py` node | Medium |
| Rate limiting | `slowapi` middleware | Small |
| Error handler middleware | Custom exception handlers | Small |
| `GET /search` unified search | New router | Medium |
| Conversation history API | New endpoint in `threads.py` | Small |

### Phase 3.3: Polish (Low Priority)

| Task | Files Affected | Effort |
|------|---------------|--------|
| Alembic migrations | `alembic/` setup | Medium |
| Async SQLAlchemy | Update `sqlite_store.py` | Medium |
| Circuit breakers for external APIs | Update services | Small |
| Prometheus metrics | `prometheus-fastapi-instrumentator` | Small |
| API versioning (`/api/v1/`) | Update all routers | Medium |
| OpenAPI documentation improvements | Router tags, descriptions | Small |
| Docker containerization | `Dockerfile`, `docker-compose.yml` | Medium |
| Health check enhancements | Update `/health` endpoint | Small |

---

## References

- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **FastAPI Best Practices**: https://fastapi.tiangolo.com/tutorial/
- **LangChain Tools**: https://python.langchain.com/docs/modules/agents/tools/
- **MCP Specification**: https://modelcontextprotocol.io/
- **SQLAlchemy 2.0**: https://docs.sqlalchemy.org/en/20/
- **APScheduler**: https://apscheduler.readthedocs.io/
- **LangSmith**: https://docs.smith.langchain.com/
- **SlowAPI Rate Limiting**: https://slowapi.readthedocs.io/
