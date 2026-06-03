# JARVIS — Documentación del Backend

## Stack
- **Framework**: FastAPI (Python 3.12)
- **LLM**: Ollama Cloud (`minimax-m2.7:cloud`) vía OpenAI-compatible API
- **Agent**: LangGraph con bind_tools nativo
- **DB**: SQLite (SQLAlchemy ORM)
- **Vector DB**: ChromaDB (notas + wiki)
- **Auth**: Google OAuth 2.0 con PKCE
- **TTS**: Piper ONNX (es_ES-sharvard-medium)
- **STT**: Groq (whisper-large-v3-turbo)

## Estructura de archivos
```
backend/
├── api/
│   ├── main.py              # FastAPI app, CORS, routers, startup
│   ├── dependencies.py      # get_jarvis_graph (lazy init)
│   └── routers/
│       ├── chat.py           # POST /chat + WS /ws/chat
│       ├── voice.py          # POST /api/v1/voice (STT → LLM → TTS)
│       ├── notes.py          # CRUD notas (/api/v1/notes)
│       ├── todos.py          # CRUD tareas
│       ├── calendar.py       # Google Calendar API
│       ├── gmail.py          # Gmail inbox/search/send
│       ├── drive.py          # Google Drive list/upload/download/delete
│       ├── auth_google.py    # OAuth: /auth/google/login, callback, status
│       ├── wiki.py           # Search/reindex Obsidian vault
│       ├── agent.py          # Agent diagnostics
│       ├── personas.py       # Lista de personalidades
│       └── files.py          # Railway Object Storage (legacy)
├── agent/
│   ├── graph.py              # LangGraph: retrieval → agent → tools loop
│   ├── nodes.py              # call_model_with_tools (bind_tools + RAG)
│   ├── state.py              # JarvisState (messages, persona, tool_iterations)
│   ├── rag_node.py           # Búsqueda semántica automática en wiki+notas
│   ├── personalities.py      # 6 personalidades, 37 herramientas c/u
│   └── tools/registry.py     # Registro central de 33 herramientas
├── services/
│   ├── google_auth.py        # OAuth PKCE (code_verifier + code_challenge)
│   ├── gmail_service.py      # Gmail API wrapper
│   ├── drive_service.py      # Google Drive API wrapper
│   ├── calendar_service.py   # Google Calendar API wrapper
│   ├── notes_service.py      # Notas CRUD + sync a ChromaDB
│   ├── tts_service.py        # Piper TTS (descarga automática)
│   └── wiki_engine.py        # ChromaDB indexing + watchdog
├── llm/
│   └── ollama_cloud.py       # ChatOpenAI → Ollama Cloud (streaming + tools)
├── service/
│   └── vector_service.py     # ChromaDB embeddings + semantic search
├── core/
│   ├── resilience.py         # Circuit breakers (LLM, Google APIs)
│   ├── middleware.py          # Request ID, logging, rate limiter
│   └── logging.py            # Loguru setup
├── models/
│   └── chat.py               # StreamChunk, ChatRequest, VoicePipelineResponse
├── storage/
│   └── sqlite_store.py       # SQLAlchemy session factory
└── config.py                 # Settings (pydantic, env vars)
```

## Flujo principal

### 1. Chat (WebSocket)
```
Cliente → WS /ws/chat
  → POST /api/v1/ws/chat (FastAPI)
    → graph.ainvoke(input_state, callbacks=[WebSocketCallback])
      → retrieval_node        # Busca en wiki + notas
      → agent_node            # LLM con bind_tools (37 tools)
      → tool_condition? YES → tool_node → agent_node (loop)
      → tool_condition? NO → END
    → WebSocketCallback.on_llm_new_token  # Streaming token por token
    → WebSocketCallback.on_tool_start     # "Usando create_note..."
    → WebSocketCallback.on_tool_end       # Resultado de herramienta
  → StreamChunk(type="done")
```

### 2. Voice
```
POST /api/v1/voice (audio webm)
  → Groq STT → transcript
  → get_llm().ainvoke(prompt voz, timeout=30s)
  → Piper TTS (opcional, fallback sin audio)
  → { transcript, response_text, audio_base64 }
```

### 3. Google OAuth
```
GET /auth/google/login
  → genera code_verifier + code_challenge (SHA256)
  → redirect a Google

Google → GET /auth/google/callback?code=...&state=...
  → POST token endpoint (client_id + secret + code + code_verifier)
  → guarda refresh_token en SQLite
  → redirect a /settings?google=connected

GET /auth/google/status
  → ¿refresh_token en DB? → { connected: true/false }
```

### 4. RAG (Second Brain)
```
Cada mensaje del usuario:
  retrieval_node()
    → semantic_search(query, top_k=5)
      → ChromaDB cosine similarity
      → Notas + Wiki combined
    → resultado como [CONOCIMIENTO] en el prompt del agente

Indexado:
  POST /api/v1/wiki/reindex
    → wiki_engine.index_vault()
      → Lee todos los .md del vault
      → Chunk (800 chars, overlap 100)
      → Embeddings con nomic-embed-text (Ollama Cloud)
      → ChromaDB batch insert

Watchdog (opcional, auto-reindex):
  POST /api/v1/wiki/watch
    → watchdog observer monitorea cambios en el vault
    → debounce 3s → reindex automático
```

## Herramientas del agente (33 tools)

| Categoría | Herramientas |
|-----------|-------------|
| **Notas** | create_note, list_notes, get_note, update_note, delete_note |
| **Tareas** | create_todo, list_todos, complete_todo, update_todo, delete_todo |
| **Wiki** | wiki_query, wiki_save_research, wiki_ingest |
| **Calendario** | list_calendar_events, create_calendar_event, update_calendar_event, delete_calendar_event |
| **Email** | search_emails, send_email, list_emails |
| **Google Suite** | list_gmail, search_gmail, send_gmail, search_drive, list_drive_files, list_calendar_google, create_calendar_event_google |
| **Memoria** | search_memory, save_memory, list_memories, delete_memory |
| **Búsqueda** | web_search, search_notes_semantic, search_wiki_semantic, search_all_knowledge |
| **Utilidad** | get_current_time, get_current_date |

## Variables de entorno (.env)
```
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL_ID=minimax-m2.7:cloud
OLLAMA_API_KEY=<key>
GROQ_API_KEY=<key>
GROQ_STT_MODEL=whisper-large-v3-turbo
PIPER_MODEL_PATH=data/voices/es_ES-sharvard-medium/es_ES-sharvard-medium.onnx
OBSIDIAN_VAULT_PATH=C:\Users\...\Obsidian\JARVIS_Vault
API_HOST=0.0.0.0
API_PORT=8001
```
