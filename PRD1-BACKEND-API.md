# PRD #1 — BACKEND API
## Proyecto: JARVIS | Stack: FastAPI + LangGraph + PostgreSQL (NeonDB) + Local LLM
### Versión: 1.0

---

## 1. VISIÓN DEL PRODUCTO

Jarvis es un asistente AI personal que corre **100% en local** usando un LLM (LM Studio en puerto 1234, compatible con OpenAI API). Se comunica con el usuario en tiempo real via WebSocket, tiene memoria persistente, y accede a herramientas del sistema (notas, tareas, calendario, email, web search).

**Referencia directa de código:**
- `backend/api/main.py` — FastAPI app con lifespan, middleware, routers
- `backend/agent/graph.py` — LangGraph con SqliteSaver checkpointer
- `backend/agent/state.py` — AgentState con mensajes, herramientas, contexto
- `backend/tools/registry.py` — Tool registry dinámico

---

## 2. ARQUITECTURA DEL BACKEND

### 2.1 Stack tecnológico

```
FastAPI (ASGI)
├── Routers: chat, agent, notes, todos, calendar, email, threads, messages, search, diagnostics, tts
├── LangGraph Agent
│   ├── State: AgentState (messages, tools, context, workspace)
│   ├── Nodes: supervisor, rag, tools
│   └── Checkpointer: SqliteSaver (MemorySaver fallback)
├── LLM Providers (factory pattern)
│   ├── bedrock (Claude via AWS)
│   ├── ollama (local/cloud)
│   └── lm_studio (local, default — puerto 1234)
├── Storage Layer (factory: STORAGE_TYPE env var)
│   ├── sqlite_store (desarrollo)
│   └── neon_store (producción PostgreSQL)
└── Tools Registry
    ├── calendar (Google Calendar sync)
    ├── email (Gmail API)
    ├── memory (vector store)
    ├── notes (CRUD notas markdown)
    ├── semantic_search (vector similarity)
    ├── todos (CRUD tareas)
    ├── utility (time, weather, calculator)
    ├── web_search (Tavily)
    └── wiki (Wikipedia)
```

### 2.2 Endpoint groups

**Chat (WebSocket) — `/api/v1/chat`**
- `WebSocket /ws` — chat bidireccional en tiempo real
- `POST /` — envíar mensaje (HTTP alternativo a WS)

**Agent — `/api/v1/agent`**
- `POST /run` — correr agente con task específica
- `POST /stream` — streaming de respuesta
- `GET /status` — estado del agente

**Notes — `/api/v1/notes`**
- `GET /` — listar notas
- `POST /` — crear nota
- `GET /{id}` — obtener nota
- `PUT /{id}` — actualizar nota
- `DELETE /{id}` — eliminar nota

**Todos — `/api/v1/todos`**
- `GET /` — listar tareas
- `POST /` — crear tarea
- `PUT /{id}` — actualizar (toggle complete, edit)
- `DELETE /{id}` — eliminar

**Calendar — `/api/v1/calendar`**
- `GET /events` — listar eventos
- `POST /events` — crear evento
- `PUT /events/{id}` — actualizar
- `DELETE /events/{id}` — eliminar

**Email — `/api/v1/emails`**
- `GET /` — listar emails (Gmail sync)
- `POST /send` — enviar email
- `GET /{id}` — ver email completo

**Threads — `/api/v1/threads`**
- `GET /` — listar threads de conversación
- `POST /` — crear thread
- `GET /{id}` — obtener thread con mensajes

**Messages — `/api/v1/messages`**
- `GET /thread/{thread_id}` — mensajes de un thread
- `POST /` — crear mensaje

**Search — `/api/v1/search`**
- `GET /?q={query}&type={type}` — búsqueda semántica

**Diagnostics — `/api/v1/diagnostics`**
- `GET /` — diagnóstico del sistema (LLM, DB, tools)

**TTS — `/api/v1/tts`**
- `POST /synthesize` — text-to-speech

### 2.3 WebSocket Protocol

El chat via WebSocket es el通道 principal. Protocolo:

```json
// Cliente → Servidor
{ "type": "message", "content": "qué fecha tenemos mañana?" }
{ "type": "ping" }

 // Servidor → Cliente
{ "type": "token", "content": "La reunión es" }
{ "type": "token", "content": " mañana a las" }
{ "type": "tool_call", "tool": "calendar", "input": {...} }
{ "type": "tool_result", "tool": "calendar", "result": {...} }
{ "type": "done" }
{ "type": "error", "message": "..." }
```

---

## 3. MODELO DE DATOS (Storage Layer)

### 3.1 Storage Factory

```python
# backend/storage/__init__.py
from backend.config import settings

def get_store():
    if settings.storage_type == "neon":
        from backend.storage.neon_store import NeonStore
        return NeonStore()
    else:
        from backend.storage.sqlite_store import SqliteStore
        return SqliteStore()
```

### 3.2 Modelos principales

**Thread** — conversación completa
```python
id: UUID (PK)
title: str
created_at: datetime
updated_at: datetime
```

**Message** — mensaje individual
```python
id: UUID (PK)
thread_id: UUID (FK → Thread)
role: str  # "user" | "assistant" | "system"
content: str
tool_calls: JSON (nullable)
tool_results: JSON (nullable)
created_at: datetime
```

**Note** — nota markdown
```python
id: UUID (PK)
title: str
content: str (markdown)
tags: list[str]
created_at: datetime
updated_at: datetime
```

**Todo** — tarea
```python
id: UUID (PK)
title: str
description: str | None
completed: bool
due_date: datetime | None
priority: str  # "low" | "medium" | "high"
created_at: datetime
updated_at: datetime
```

**CalendarEvent** — evento de calendario
```python
id: UUID (PK)
title: str
description: str | None
start_time: datetime
end_time: datetime
location: str | None
created_at: datetime
updated_at: datetime
```

**EmailMessage** — email (Gmail sync)
```python
id: UUID (PK)
gmail_id: str | None
thread_id: str | None
from_address: str
to_address: list[str]
subject: str
body: str
body_html: str | None
received_at: datetime
created_at: datetime
```

---

## 4. LANGGRAPH AGENT

### 4.1 Graph Structure

```
┌─────────────┐
│  supervisor │ (nodo raíz — decide qué hacer)
└──────┬──────┘
       │
   ┌───┴───┐
   ▼       ▼
┌─────┐  ┌──────────┐
│ rag │  │  tools   │ (llama herramientas)
└─────┘  └────┬─────┘
              │
         ┌────┴────┐
         ▼         ▼
    calendar   notes, todos, etc.
```

### 4.2 AgentState

```python
class AgentState(TypedDict):
    messages: list[BaseMessage]  # historial de conversación
    tools: list[BaseTool]        # herramientas disponibles
    tool_results: list[dict]     # resultados de herramientas
    workspace: dict              # contexto del workspace
    current_task: str | None     # tarea actual
    next_action: str             # "continue" | "respond" | "wait"
```

### 4.3 Supervisor Node

El supervisor decide en cada paso:
1. Si hay tool_calls pendientes → ejecutar herramientas
2. Si el último mensaje requiere búsqueda → llamar RAG
3. Si la respuesta está lista → responder al usuario
4. Si necesita más info → pedir clarificación

### 4.4 Tool Registry

Todas las herramientas seguem el formato LangChain tool:

```python
@tool
def get_calendar_events(start_date: str, end_date: str) -> list[dict]:
    """Get calendar events in date range. Format: YYYY-MM-DD"""
    ...
```

Las herramientas disponibles van en `AgentState.tools` y se injectan en el prompt del LLM.

### 4.5 Checkpointer

```python
# SqliteSaver para persistencia de conversación
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("data/checkpoints.db")
# Fallback a MemorySaver si falla
```

---

## 5. LLM PROVIDERS

### 5.1 Factory Pattern

```python
# backend/llm/__init__.py
from backend.config import settings

def get_llm():
    if settings.llm_provider == "bedrock":
        from backend.llm.bedrock import BedrockLLM
        return BedrockLLM()
    elif settings.llm_provider == "ollama":
        from backend.llm.ollama import ChatOllama
        return ChatOllama()
    elif settings.llm_provider == "lm_studio":
        from backend.llm.lm_studio import LMStudioLLM
        return LMStudioLLM()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

### 5.2 LM Studio (DEFAULT)

- Base URL: `http://127.0.0.1:1234/v1`
- Model: `qwen/qwen2.5-vl-7b` (hardcoded en `lm_studio.py:21`)
- Compatible con OpenAI Chat Completions API

### 5.3 Ollama

- Base URL: configurable via `OLLAMA_BASE_URL`
- Model: configurable via `OLLAMA_MODEL_ID`

### 5.4 Bedrock (Claude)

- Region: `us-east-1` (configurable)
- Model: `us.anthropic.claude-sonnet-4-5`

---

## 6. CONFIGURACIÓN

### 6.1 Environment Variables (.env)

```env
# LLM Provider
LLM_PROVIDER=lm_studio
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1

# Storage
STORAGE_TYPE=neon
DATABASE_URL=postgresql://neondb_owner:npg_xxx@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require

# Storage alternativa (desarrollo)
# STORAGE_TYPE=sqlite
# DATA_DIR=data

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# Auth
JWT_SECRET_KEY=change-this-in-production

# Optional
ENABLE_LANGSMITH=false
TAVILY_API_KEY=
OBSIDIAN_VAULT_PATH=
```

### 6.2 NeonDB Connection

```python
# STORAGE_TYPE=neon activa el NeonStore
# Requiere: psycopg2 o asyncpg en requirements
# Connection string completo en .env
```

---

## 7. ERROR HANDLING

### 7.1 Exception Hierarchy

```python
class AppError(Exception):
    """Base exception for all app errors."""
    def __init__(self, message: str, code: str, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}

class RateLimitExceeded(AppError):
    code = "rate_limit_exceeded"

class ToolExecutionError(AppError):
    code = "tool_execution_error"

class LLMError(AppError):
    code = "llm_error"
```

### 7.2 HTTP Exception Handlers

En `main.py` se registran handlers para:
- `RequestValidationError` → 422 con detalle
- `HTTPException` → 4xx/5xx con cuerpo JSON
- `AppError` → código personalizado
- `Exception` genérica → 500

---

## 8. MIDDLEWARE

### 8.1 Middleware Stack (orden de ejecución)

1. **GZipMiddleware** — comprime responses > 1KB
2. **CORSMiddleware** — permite origins configurados
3. **RequestIDMiddleware** — inyecta `X-Request-ID` header
4. **RequestResponseLoggingMiddleware** — loguea requests/responses

### 8.2 Rate Limiting

- Default: 100/minuto
- Chat: 10/minuto
- Agent: 20/minuto

Librería: `slowapi`

---

## 9. HEALTH CHECKS

```
GET /api/v1/health         → { "status": "ok" }
GET /api/v1/health/ready   → { "status": "ready", "checks": {...} }
GET /api/v1/health/live    → { "status": "alive" }
```

Readiness check verifica:
- Database (query SELECT 1)
- LLM provider (intentar cargar modelo)
- Circuit breakers

---

## 10. API RESPONSE FORMAT

### Success
```json
{ "data": {...}, "meta": { "request_id": "..." } }
```

### Error
```json
{
  "error": {
    "code": "validation_error",
    "message": "Human readable message",
    "details": {...}
  }
}
```

---

## 11. DEPENDENCIAS

```
fastapi
uvicorn
pydantic
pydantic-settings
python-dotenv
loguru
slowapi
langgraph
langchain-core
langchain-community
httpx
websockets
sqlalchemy
aiosqlite
psycopg2-binary
# ó asyncpg para NeonDB async
```

---

## 12. PRÓXIMOS PASOS

1. [ ] Verificar que NeonDB connection string funciona
2. [ ] Implementar migraciones con Alembic para NeonDB
3. [ ] Crear endpoint `/api/v1/agent/stream` con Server-Sent Events
4. [ ] Implementar rate limiting por workspace
5. [ ] Agregar autenticación JWT a todos los endpoints