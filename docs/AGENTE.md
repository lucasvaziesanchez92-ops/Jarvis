# JARVIS — Documentación del Agente

## Arquitectura

```
usuario
  ↓
WebSocket /ws/chat
  ↓
graph.ainvoke(input_state)
  ↓
┌──────────────┐
│ retrieval    │ ← Busca contexto en wiki + notas (ChromaDB)
└──────┬───────┘
       ↓
┌──────────────┐
│ agent        │ ← LLM con bind_tools (37 herramientas)
│              │    System prompt: personalidad + instrucciones
│              │    Contexto: [CONOCIMIENTO] si hay RAG
└──────┬───────┘
       ↓
 tools_condition(state)
       ↓
  YES → ┌──────────┐
        │ tools    │ ← Ejecuta tool_calls nativas
        └────┬─────┘
             ↓
        agent (loop, máx 5 iteraciones)
       ↓
  NO → END
       ↓
  WebSocketCallback.on_llm_new_token (streaming)
```

## Componentes del agente

### 1. JarvisState
```python
class JarvisState(MessagesState):
    user_id: str | None
    session_id: str | None
    persona: str = "profesional"
    retrieved_context: list[str]   # Contexto del RAG
    tool_iterations: int           # Contador de herramientas usadas
```

### 2. retrieval_node (RAG)
- Se ejecuta **siempre** al inicio de cada mensaje
- Busca en ChromaDB (`backend/service/vector_service.py`)
- Usa embeddings de `nomic-embed-text` (Ollama Cloud)
- Si encuentra resultados, los formatea como `[CONOCIMIENTO]` y los pasa al agente

### 3. agent_node
- Obtiene personalidad del usuario → system prompt
- Filtra herramientas permitidas (todas las personalidades tienen 37 tools con `ALL_ALLOWED`)
- `get_llm()` → `ChatOpenAI(model="minimax-m2.7:cloud")`
- `llm.bind_tools(tools)` → llama a Ollama Cloud con function calling nativo
- Si `bind_tools` falla (ej. 400), usa `invoke()` plano
- Máximo 5 iteraciones de herramientas por mensaje

### 4. tool_node
- Recibe los `tool_calls` del AIMessage
- Busca la herramienta en el registry → `tool.invoke(args)`
- Devuelve `ToolMessage` con el resultado
- Incrementa `tool_iterations`

### 5. WebSocketCallback (streaming)
```python
class WebSocketCallback(BaseCallbackHandler):
    def on_llm_new_token(self, token):
        # Envía type="stream" con cada token generado
    
    def on_tool_start(self, serialized, input_str):
        # Envía type="tool_start" cuando el modelo decide usar herramienta
    
    def on_tool_end(self, output):
        # Envía type="tool_end" con el resultado
```

## Personalidades

| Nombre | Tono | Tools |
|--------|------|-------|
| profesional | Directo, sin vueltas | 37 |
| amigable | Cálido, cercano | 37 |
| tecnica | Técnico, preciso | 37 |
| ejecutiva | Breve, bullet points | 37 |
| creativa | Ideas, brainstorming | 37 |
| soporte | Paciente, paso a paso | 37 |

**Todas las personalidades tienen acceso a las 37 herramientas.** La diferencia está en el system prompt y el tono.

## Herramientas disponibles (33 tools, 37 nombres permitidos)

### Notas (5)
`create_note` `list_notes` `get_note` `update_note` `delete_note`

### Tareas (5)
`create_todo` `list_todos` `complete_todo` `update_todo` `delete_todo`

### Wiki / Second Brain (3)
`wiki_query` `wiki_save_research` `wiki_ingest`

### Google Calendar (8)
`list_calendar_events` `create_calendar_event` `update_calendar_event` `delete_calendar_event`
`list_calendar_google` `create_calendar_event_google`

### Gmail / Email (6)
`search_emails` `send_email` `list_emails`
`search_gmail` `send_gmail` `list_gmail`

### Google Drive (2)
`search_drive` `list_drive_files`

### Memoria (4)
`search_memory` `save_memory` `list_memories` `delete_memory`

### Búsqueda (4)
`web_search` `search_notes_semantic` `search_wiki_semantic` `search_all_knowledge`

### Utilidad (2)
`get_current_time` `get_current_date`

## System Prompt (profesional)
```
Sos JARVIS, un asistente de IA que vive dentro de un chat.
Tu objetivo es ayudar al usuario de forma directa, natural y eficiente.

REGLAS IMPORTANTES:
1. Usá las herramientas SIN PREGUNTAR. Si el usuario dice 'creá una nota',
   ejecutá create_note directamente.
2. Buscá en wiki_query cuando necesites contexto (SEGUNDO CEREBRO).
3. NUNCA digas 'no tengo herramientas para eso'. Tenés +30.
4. Las notas se crean con create_note, NO en Drive.
5. Sé breve. 2-3 oraciones.
6. NUNCA te quedes sin responder.
```

## Modelo LLM
- **Provider**: Ollama Cloud → OpenAI-compatible API
- **Modelo**: `minimax-m2.7:cloud`
- **Config**: temperature=0.5, max_tokens=1024, timeout=30s, streaming=True
- **Tools**: function calling nativo (probado y funcionando)
- **Latencia**: ~5-8s por llamada al LLM, ~15-25s para un ciclo completo agent→tools→agent

## RAG (Retrieval-Augmented Generation)
- **Vector DB**: ChromaDB persistente en `data/chroma_db/`
- **Embeddings**: HuggingFace `all-MiniLM-L6-v2` (local) o `nomic-embed-text` (Ollama Cloud)
- **Indexado**: Markdown → chunks de 800 caracteres con overlap de 100
- **Watchdog**: Monitorea cambios en el vault de Obsidian (debounce 3s)

## Checkpointer
- `MemorySaver` — persiste el estado de la conversación en memoria
- Thread ID por session_id → mantiene contexto entre mensajes

## Limitaciones actuales
- **minimax-m2.7:cloud** es lento (5-8s por call). Con 2-3 iteraciones = 15-25s
- Las herramientas son **síncronas** (bloquean el event loop de FastAPI)
- No hay paralelización de herramientas (se ejecutan secuencialmente)
- El checkpointer es en memoria (se pierde al reiniciar el backend)
