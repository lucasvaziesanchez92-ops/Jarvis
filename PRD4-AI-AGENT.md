# PRD #4 — AI AGENT: LANGGRAPH + LLM
## Proyecto: JARVIS | Stack: LangGraph + Local LLM (LM Studio/Ollama/Bedrock)
### Versión: 1.0

---

## 1. VISIÓN DEL PRODUCTO

El agente de Jarvis es un sistema autónomo basado en LangGraph que recibe mensajes del usuario, decide qué herramientas usar, y genera respuestas. Corre 100% en local usando LM Studio (OpenAI-compatible API en puerto 1234) como LLM default, con soporte para Ollama y AWS Bedrock.

**Referencia directa de código:**
- `backend/agent/graph.py` — LangGraph con StateGraph, ToolNode, SqliteSaver
- `backend/agent/state.py` — JarvisState (extiende MessagesState)
- `backend/agent/nodes.py` — call_model_with_tools
- `backend/agent/rag_node.py` — retrieval_node para RAG
- `backend/tools/registry.py` — CORE_TOOLS, EXTENDED_TOOLS, ALL_TOOLS

---

## 2. LANGGRAPH ARCHITECTURE

### 2.1 Graph Structure

```
┌────────────┐     ┌─────────────┐     ┌────────────┐
│    START   │────▶│  retrieval  │────▶│    agent   │
└────────────┘     └─────────────┘     └──────┬─────┘
                                              │
                         ┌─────────────────────┼─────────────────────┐
                         │                     │                     │
                         ▼                     ▼                     ▼
                    ┌────────┐          ┌───────────┐          ┌──────┐
                    │  tool  │          │ tools_condition │     │ END  │
                    │ (ToolNode) │◀─────│ (edges)   │          └──────┘
                    └────┬───┘        └───────────┘
                         │
                         └──────────────────┐
                                            ▼
                                      ┌─────────┐
                                      │  agent  │ (loop)
                                      └─────────┘
```

### 2.2 Node Descriptions

**retrieval node**
- Ejecuta RAG (Retrieval Augmented Generation)
- Busca contexto relevante en memoria externa (wiki, notes)
- Agrega contexto al estado como `retrieved_context`

**agent node**
- Nodo principal — llama al LLM con tools
- Usa `get_contextual_tools()` para seleccionar tools relevantes según input
- Llama `call_model_with_tools(state, llm_with_tools, extra_context)`

**tools node**
- ToolNode de langgraph.prebuilt
- Ejecuta las herramientas seleccionadas por el modelo
- results van al estado como `tool_results`

### 2.3 Conditional Edges

```python
builder.add_conditional_edges("agent", tools_condition)
# tools_condition: si hay tool_calls → ir a "tools", si no → END
```

---

## 3. AGENT STATE

### 3.1 JarvisState (extends MessagesState)

```python
class JarvisState(MessagesState):
    """Extends MessagesState with user/session tracking and RAG context."""

    # Heredado de MessagesState:
    messages: list[BaseMessage]  # historial de mensajes

    # Propios:
    user_id: str | None = None
    session_id: str | None = None
    retrieved_context: Annotated[list[str], operator.add] = []
```

**MessagesState** (de langgraph.graph):
```python
class MessagesState(TypedDict):
    messages: Annotated[list, add_messages]
```

El operador `add_messages` permite append al historial.

---

## 4. TOOL REGISTRY

### 4.1 Tool Categories

**CORE_TOOLS** — siempre disponibles:
```python
CORE_TOOLS = [
    wiki_query,
    wiki_save_research,
    web_search,
    list_notes,
    create_note,
    list_todos,
    create_todo,
    complete_todo,
    get_current_time,
    # + semantic search si langchain_chroma disponible
]
```

**EXTENDED_TOOLS** — solo si el contexto lo requiere:
```python
EXTENDED_TOOLS = [
    list_calendar_events,
    create_calendar_event,
    search_emails,
    send_email,
    wiki_ingest,
]
```

**ALL_TOOLS** = CORE_TOOLS + EXTENDED_TOOLS

### 4.2 Dynamic Tool Selection

```python
def get_contextual_tools(input_text: str) -> list:
    """Selecciona herramientas basadas en el contexto para ahorrar tokens."""
    input_text = input_text.lower()
    tools = list(CORE_TOOLS)

    if any(word in input_text for word in ["correo", "email", "escribe", "enviar"]):
        tools.extend([t for t in EXTENDED_TOOLS if "email" in str(t.name)])

    if any(word in input_text for word in ["calendario", "reunión", "evento", "cita"]):
        tools.extend([t for t in EXTENDED_TOOLS if "calendar" in str(t.name)])

    return tools
```

### 4.3 Lazy Import for Semantic Search

```python
try:
    from backend.tools.semantic_search import ...
    _SEMANTIC_AVAILABLE = True
except Exception:
    _SEMANTIC_AVAILABLE = False
    # Semantic tools excluded
```

---

## 5. LLM PROVIDERS

### 5.1 Factory: get_llm()

```python
# backend/llm/__init__.py
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
```

### 5.2 LM Studio (DEFAULT)

```python
# backend/llm/lm_studio.py
base_url = "http://127.0.0.1:1234/v1"
model = "qwen/qwen2.5-vl-7b"  # HARDCODED — debería usar settings
```
**ISSUE:** Model hardcoded in `lm_studio.py:21`. Should use `settings.lm_studio_model`.

### 5.3 Ollama

```python
# backend/llm/ollama.py
base_url = settings.ollama_base_url  # http://localhost:11434
model = settings.ollama_model        # llama3.2
```

### 5.4 Bedrock (Claude)

```python
# backend/llm/bedrock.py
region = settings.aws_region         # us-east-1
model = settings.bedrock_model_id    # us.anthropic.claude-sonnet-4-5
```

---

## 6. CHECKPOINTER

### 6.1 SqliteSaver (Production)

```python
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    CHECKPOINTER = SqliteSaver.from_conn_string("file:data/langgraph.db?mode=rwc")
    print("[checkpointer] SqliteSaver activated (real persistence)")
except Exception:
    from langgraph.checkpoint.memory import MemorySaver
    CHECKPOINTER = MemorySaver()
    print("[checkpointer] MemorySaver (volatile — no persistence across restarts)")
```

**Storage:** `data/langgraph.db` (SQLite file)
**Benefit:** Conversaciones persisten entre reinicios del servidor.

### 6.2 MemorySaver (Fallback)

Si SqliteSaver falla (ej: directorio `data/` no existe), cae a MemorySaver que es volatil.

---

## 7. RAG NODE

### 7.1 retrieval_node

```python
# backend/agent/rag_node.py
async def retrieval_node(state: JarvisState):
    """Busca contexto relevante y lo agrega al estado."""
    last_message = state["messages"][-1].content
    retrieved = await search_all_knowledge(last_message)  # vector search
    return {"retrieved_context": retrieved}
```

### 7.2 Integration

El nodo `retrieval` corre antes de `agent` en el graph:

```python
builder.add_edge(START, "retrieval")
builder.add_edge("retrieval", "agent")
```

---

## 8. AGENT NODE

### 8.1 dynamic_agent_node

```python
def dynamic_agent_node(state: JarvisState):
    last_msg = state["messages"][-1].content if state["messages"] else ""
    relevant_tools = get_contextual_tools(last_msg)

    retrieved = state.get("retrieved_context", [])
    context_note = ""
    if retrieved:
        context_note = (
            "\n\n[CONOCIMIENTO RELEVANTE OBTENIDO DE TU MEMORIA EXTERNA]\n"
            + "\n".join(retrieved)
            + "\n[/CONOCIMIENTO RELEVANTE]\n\n"
        )

    llm = get_llm()
    llm_with_tools = llm.bind_tools(relevant_tools)

    return call_model_with_tools(state, llm_with_tools=llm_with_tools, extra_context=context_note)
```

### 8.2 Extra Context Injection

El contexto de RAG se inyecta como `extra_context` al llamar el modelo, para que el LLM tenga info relevante sin necesidad de tool calls.

---

## 9. CALL_MODEL_WITH_TOOLS

```python
# backend/agent/nodes.py
def call_model_with_tools(state: JarvisState, llm_with_tools, extra_context: str = ""):
    """Invoca el LLM con tools y contexto adicional."""
    # Prepara mensajes
    # Inject extra_context como system message o prefix
    # Invoca llm_with_tools.invoke(messages)
    # Retorna {"messages": [ AIMessage(...)]}
```

---

## 10. GRAPH COMPILATION

```python
def build_autonomous_graph(tools=None):
    builder = StateGraph(JarvisState)
    active_tools = tools if tools is not None else ALL_TOOLS

    builder.add_node("retrieval", retrieval_node)
    builder.add_node("agent", dynamic_agent_node)
    builder.add_node("tools", ToolNode(active_tools))

    builder.add_edge(START, "retrieval")
    builder.add_edge("retrieval", "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=checkpointer)
```

---

## 11. GRAPH CACHING

```python
_graph = None

def get_graph(tools=None):
    global _graph
    if _graph is None or tools is not None:
        _graph = build_autonomous_graph(tools=tools)
    return _graph
```

El graph se caching en memoria. Si se llama con `tools=` diferente, se rebuild.

---

## 12. TOOLS DEFINITIONS

### 12.1 Notes Tools

```python
@tool
def create_note(title: str, content: str, tags: list[str] = None) -> dict:
    """Create a new note. Args: title (required), content (required), tags (optional)."""
    ...

@tool
def list_notes(limit: int = 50) -> list[dict]:
    """List all notes. Returns up to `limit` notes ordered by creation date."""
    ...

@tool
def get_note(note_id: str) -> dict:
    """Get a specific note by ID."""
    ...
```

### 12.2 Todos Tools

```python
@tool
def create_todo(text: str, priority: str = "medium", due_date: str = None) -> dict:
    """Create a new todo. Args: text (required), priority (low/medium/high), due_date (YYYY-MM-DD)."""
    ...

@tool
def list_todos(limit: int = 50) -> list[dict]:
    """List all todos. Returns up to `limit` todos ordered by creation date."""
    ...

@tool
def complete_todo(todo_id: str) -> dict:
    """Mark a todo as completed by ID."""
    ...
```

### 12.3 Calendar Tools

```python
@tool
def list_calendar_events(start_date: str, end_date: str) -> list[dict]:
    """Get calendar events in date range. Format: YYYY-MM-DD"""
    ...

@tool
def create_calendar_event(title: str, start_time: str, end_time: str, description: str = None, location: str = None) -> dict:
    """Create a calendar event. Dates in ISO format."""
    ...
```

### 12.4 Email Tools

```python
@tool
def search_emails(query: str, limit: int = 10) -> list[dict]:
    """Search emails by query string."""
    ...

@tool
def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email. Args: to (required), subject (required), body (required)."""
    ...
```

### 12.5 Utility Tools

```python
@tool
def get_current_time() -> str:
    """Get current date and time. No arguments required."""
    ...
```

### 12.6 Web Search Tool

```python
@tool
def web_search(query: str) -> str:
    """Search the web for information. Use when you need current info not in your knowledge."""
    ...
```

### 12.7 Wiki Tools

```python
@tool
def wiki_query(query: str) -> str:
    """Query Wikipedia for information. Use for general knowledge questions."""

@tool
def wiki_save_research(topic: str, summary: str) -> dict:
    """Save research findings to your knowledge base."""

@tool
def wiki_ingest(url: str) -> dict:
    """Ingest web content into knowledge base from a URL."""
```

---

## 13. CONFIGURATION

### 13.1 Environment Variables

```env
# LLM Provider
LLM_PROVIDER=lm_studio
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1

# Ollama (alternative)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_ID=llama3.2

# Bedrock (alternative)
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5

# Optional
TAVILY_API_KEY=  # for web search
ENABLE_LANGSMITH=false
LANGSMITH_API_KEY=
```

### 13.2 Lazy Graph Warmup

En `backend/api/main.py` lifespan:

```python
try:
    from backend.api.dependencies import get_jarvis_graph
    get_jarvis_graph()
    logger.info("Graph pre-warmed successfully")
except Exception as e:
    logger.warning(f"Graph pre-warm failed (LLM may not be running): {e}")
```

El graph se pre-calienta al startup para que la primera request sea rápida.

---

## 14. KNOWN ISSUES

### 14.1 Hardcoded Model

```python
# backend/llm/lm_studio.py:21
model = "qwen/qwen2.5-vl-7b"  # Should use settings.lm_studio_model
```

**Fix needed:** Usar `settings.lm_studio_model` en vez del hardcoded value.

### 14.2 Semantic Search

```python
# backend/tools/registry.py
try:
    from backend.tools.semantic_search import ...
    _SEMANTIC_AVAILABLE = True
except Exception:
    _SEMANTIC_AVAILABLE = False
```

Si `langchain_chroma` no está instalado, las semantic tools no están disponibles.

---

## 15. PRÓXIMOS PASOS

1. [ ] Fix hardcoded model en `lm_studio.py` — usar settings
2. [ ] Agregar streaming support en agent (Server-Sent Events)
3. [ ] Implementar session management con user_id/session_id
4. [ ] Agregar más tools: file read/write, system commands
5. [ ] Implementar tool retry logic con exponential backoff
6. [ ] Agregar observability con LangSmith (cuando `ENABLE_LANGSMITH=true`)