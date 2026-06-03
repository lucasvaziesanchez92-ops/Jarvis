# PROJECT CONTEXT — Jarvis AI Personal Assistant
## Contexto Completo para Migración a Next.js

**Fecha generada:** 29 Abril 2026
**Objetivo de este documento:** Proveer contexto ARCHIVAL detallado de cada archivo del proyecto, para facilitar la migración completa a Next.js y preservar el estado actual.

---

## 1. Stack Tecnológico

### Backend (Python)
| Tecnología | Versión | Proposito |
|------------|---------|-----------|
| Python | 3.14 (warning: Pydantic V1 incompatible) | Lenguaje principal |
| FastAPI | >=0.115.0 | API REST + WebSocket |
| LangGraph | ==1.1.2 | Grafo de agente con tool calling |
| LangChain Core | ==1.2.20 | Base de abstracciones LLM |
| LangChain OpenAI | >=0.2.0 | ChatOpenAI (para LM Studio) |
| LangChain Ollama | >=0.2.2 | ChatOllama (⚠️ roto, hackeado) |
| LangChain AWS | >=1.4.0 | Bedrock |
| SQLAlchemy | >=2.0.0 | ORM + SQLite |
| Alembic | >=1.13.0 | Migrations |
| Pydantic v2 | >=2.10.6 | Models + Settings |
| Loguru | >=0.7.2 | Logging estructurado |
| Uvicorn | >=0.32.0 | Servidor ASGI |
| ChromaDB | >=0.4.22 | Vector store (wiki) |
| boto3 | >=1.42.0 | AWS SDK |
| google-auth | >=2.35.0 | Gmail/Calendar OAuth |
| python-jose | >=3.3.0 | JWT (no aplica en routers) |
| slowapi | >=0.1.9 | Rate limiting |
| tenacity | >=8.2.3 | Retry logic |
| pybreaker | >=1.0.2 | Circuit breaker |
| websockets | >=13.0 | Native WS support |

### Frontend Web Actual (React + Vite)
| Tecnología | Versión | Proposito |
|------------|---------|-----------|
| React | ^18.2.0 | UI |
| Vite | ^5.0.0 | Build tool |
| TypeScript | ^5.3.0 | Types |
| Three.js | ^0.160.0 | Cerebro 3D |
| @react-three/fiber | ^8.15.0 | React renderer para Three.js |
| @react-three/drei | ^9.92.0 | Helpers R3F |
| @react-three/postprocessing | ^2.19.1 | Bloom, etc. |
| Zustand | ^4.4.0 | State management |

### Mobile (Expo + React Native)
| Tecnología | Versión | Proposito |
|------------|---------|-----------|
| Expo SDK | ~51.0.0 | Framework mobile |
| React Native | 0.74.5 | UI nativa |
| React Navigation | ^6.x | Bottom tabs + stacks |
| Axios | ^1.7.7 | HTTP client |
| Zustand | ^5.0.12 | State (persistencia local) |
| date-fns | ^3.6.0 | Date formatting |
| expo-speech-recognition | ^3.1.3 | Voz a texto |

---

## 2. Estructura Completa de Archivos

```
jarvis/                                     ← Raiz del proyecto
├── .env                                    ← Configuración actual (LM Studio)
├── .env.example                            ← Template de .env
├── .gitignore
├── .pre-commit-config.yaml                 ← Hooks de pre-commit (black, ruff, etc.)
├── alembic.ini                             ← Config de migrations Alembic
├── docker-compose.yml                      ← Docker compose (api + ollama + chroma optional)
├── Dockerfile                              ← Docker build del backend
├── Makefile                                ← Comandos de build/test (Python)
├── pytest.ini                              ← Config de pytest
├── README.md                               ← Quickstart (⚠️ tiene rutas incorrectas)
│
├── PRD1-frontend.md                        ← Product Requirements Doc: Frontend
├── PRD2-backend.md                         ← PRD: Backend (fases 1-4)
├── PRD3-agent.md                           ← PRD: Agente AI
│
├── docs/
│   ├── VERIFICACION-COMPLETA.md            ← Estado verificado (11 Abr 2026) ← MUY IMPORTANTE
│   ├── architecture.md
│   ├── api-contract.md
│   └── tools.md
│
│
# ═══════════════════════════════════════════════
# BACKEND PYTHON (Mantiene como API separada)
# ═══════════════════════════════════════════════
│
├── backend/
│   ├── config.py                           ← Pydantic Settings (.env loader)
│   │                                       ← Lee .env de RAIZ (no de backend/)
│   │                                       ← ⚠️ El README dice usar `cd backend` pero .env está en root
│   │
│   ├── mcp_server.py                       ← Server MCP (Model Context Protocol) para Claude Desktop
│   │                                       ← Permite que Claude Desktop use tools de Jarvis via MCP
│   │
│   ├── __init__.py
│   │
│   ├── agent/                              ← LangGraph agent
│   │   ├── graph.py                        ← StateGraph build + compile con MemorySaver
│   │   │                                   ← ⚠️ MemorySaver = volátil (no persiste al reiniciar)
│   │   │                                   ← Debería usar SqliteSaver según PRD2
│   │   ├── nodes.py                        ← call_model(), call_model_with_tools()
│   │   │                                   ← Importa get_llm del factory (NO de bedrock directo) ✅
│   │   ├── prompts.py                      ← SYSTEM_PROMPT
│   │   ├── rag_node.py                     ← retrieval_node (RAG con ChromaDB)
│   │   ├── router.py                       ← Router node para decidir intención
│   │   ├── state.py                        ← JarvisState (TypedDict)
│   │   └── __init__.py
│   │
│   ├── api/                                ← FastAPI
│   │   ├── main.py                         ← App FastAPI con lifespan, CORS, routers, static files
│   │   │                                   ← Lifespan pre-warms graph con get_jarvis_graph()
│   │   │                                   ← ⚠️ Si LM Studio no está corriendo, esto crashea en startup
│   │   │                                   ← Monta /static con web/dist/
│   │   ├── dependencies.py                 ← get_jarvis_graph() singleton
│   │   ├── __init__.py
│   │   ├── routers/                        ← Todos los endpoints
│   │   │   ├── agent.py                    ← POST /agent/run (para mobile)
│   │   │   ├── auth.py                     ← Auth router (creado pero NO montado en main.py)
│   │   │   ├── calendar.py                 ← CRUD de eventos (requiere OAuth Google)
│   │   │   ├── chat.py                     ← POST /chat (blocking) + WS /ws/chat (streaming)
│   │   │   ├── diagnostics.py            ← GET /diagnostics/status
│   │   │   ├── email.py                    endpoints de Gmail (requiere OAuth)
│   │   │   ├── messages.py               ← CRUD de mensajes de threads
│   │   │   ├── notes.py                  ← CRUD de notas (SQLite)
│   │   │   ├── search.py                 ← Semantic search con ChromaDB
│   │   │   ├── threads.py                ← Threads de conversación
│   │   │   ├── todos.py                  ← CRUD de tareas (SQLite)
│   │   │   ├── tts.py                    ← Text-to-speech service
│   │   │   ├── __init__.py
│   │   │   └── __pycache__/
│   │   ├── templates/
│   │   │   └── debug_ui.html             ← Template HTML de debug (legacy?)
│   │   └── __pycache__/
│   │
│   ├── core/                               ← Infra estructural
│   │   ├── audit.py                        ← Audit logging
│   │   ├── auth.py                         ← JWT verification + API key (no aplica en routers)
│   │   ├── exceptions.py                   ← Custom AppError + handlers
│   │   ├── logging.py                      ← setup_logging() con loguru
│   │   ├── middleware.py                   ← RequestIDMiddleware, RequestResponseLoggingMiddleware
│   │   ├── rate_limiter.py                 ← SlowAPI limiter
│   │   ├── resilience.py                   ← Circuit breakers
│   │   ├── token_counter.py                ← Contador de tokens
│   │   ├── utils.py                        ← Utilities
│   │   └── __init__.py
│   │
│   ├── data/                               ← ⚠️ Database + data (no trackear en git)
│   │
│   ├── llm/                                ← LLM Factory
│   │   ├── bedrock.py                      ← ChatBedrock (AWS)
│   │   ├── lm_studio.py                    ← ChatOpenAI (configurado para LM Studio local)
│   │   │                                   ← Model hardcodeado: "qwen/qwen2.5-vl-7b"
│   │   ├── ollama.py                       ← ⚠️ HACKED: redirige FORZOSAMENTE a lm_studio
│   │   │                                   ← Esto está ROTO — ChatOllama debería estar aquí
│   │   ├── __init__.py                     ← Factory: get_llm() según settings.llm_provider
│   │   └── __pycache__/
│   │
│   ├── models/                             ← Pydantic models (DB + API)
│   │   ├── calendar_event.py
│   │   ├── chat.py
│   │   ├── email_message.py
│   │   ├── message.py
│   │   ├── note.py
│   │   ├── thread.py
│   │   ├── todo.py
│   │   └── __init__.py
│   │
│   ├── scripts/                            ← Scripts utilitarios
│   │   ├── reindex_knowledge.py            ← Reindexa ChromaDB
│   │   └── seed_data.py                    ← Seeds de test
│   │
│   ├── service/
│   │   └── vector_service.py               ← Servicio de vector search (ChromaDB)
│   │
│   ├── services/                           ← Business logic
│   │   ├── calendar_service.py             ← Google Calendar integration
│   │   ├── email_service.py                ← Gmail integration
│   │   ├── memory_service.py               ← Memoria del agente
│   │   ├── messages_service.py
│   │   ├── notes_service.py
│   │   ├── threads_service.py
│   │   ├── todos_service.py
│   │   ├── tts_service.py                ← Text-to-speech (¿qué motor usa?)
│   │   └── __init__.py
│   │
│   ├── storage/                            ← Persistencia
│   │   ├── sqlite_store.py                 ← SQLAlchemy engine + session factory
│   │   │                                   ← Crea tablas automáticamente con Base.metadata.create_all()
│   │   │                                   ← data/jarvis.db
│   │   ├── json_store.py                   ← Storage JSON legacy (archivo plano)
│   │   └── __init__.py
│   │
│   ├── tools/                              ← 23 tools del agente
│   │   ├── calendar.py                     ← 5 tools (create, list, get, update, delete)
│   │   ├── email.py                        ← 4 tools (list, get, send, search)
│   │   ├── memory.py                       ← Memoria del agente (¿qué hace?)
│   │   ├── notes.py                        ← 5 tools
│   │   ├── registry.py                     ← ALL_TOOLS + CORE_TOOLS + EXTENDED_TOOLS
│   │   ├── semantic_search.py              ← Busqueda semantica (ChromaDB lazy import)
│   │   ├── todos.py                        ← 5 tools
│   │   ├── utility.py                      ← Utilidades del agente
│   │   ├── web_search.py                   ← Web search (Tavily / DuckDuckGo fallback)
│   │   ├── wiki.py                         ← Wiki tools (query, save, ingest)
│   │   └── __init__.py
│   │
│   └── __pycache__/
│
│
# ═══════════════════════════════════════════════
# FRONTEND WEB ACTUAL (React 18 + Vite)
# MIGRAR ESTO A NEXT.JS
# ═══════════════════════════════════════════════
│
├── web/                                    ← Frontend web actual (MIGRAR A NEXT.JS)
│   ├── index.html                          ← Entry point: App.tsx (chat + cerebro)
│   ├── brain.html                          ← Entry point: brain.tsx ( solo cerebro 3D)
│   ├── vite.config.ts                      ← Vite config (base: './')
│   │                                       ← Build con 2 entry points: main + brain
│   │
│   ├── package.json                        ← Deps: React 18, Three.js, R3F, R3P, Zustand 4
│   ├── public/                             ← Assets estáticos
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   │
│   ├── src/
│   │   ├── App.tsx                         ← App principal: Chat + NeuralBrain
│   │   │                                   ← WebSocket a ws://localhost:8000/ws/chat
│   │   ├── brain.tsx                       ← Entry point standalone del cerebro (expoort default?)
│   │   ├── main.tsx                        ← Entry point ReactDOM
│   │   │
│   │   ├── brain/                          ← 🚨 NO EXISTE (en app.tsx solo import NeuralBrain)
│   │   │                                   ← ¿Hay codigo de cerebro en App.tsx? Revisar.
│   │   │
│   │   ├── components/
│   │   │   ├── NeuralBrain.tsx             ← CEREBRO 3D (613 líneas) ← HERO DEL PROYECTO
│   │   │   │                                   ← Brain-shaped particles (NO esfera)
│   │   │   │                                   ←brainTransform() funcion matemática
│   │   │   │                                   ← ShaderMaterial custom para organic folds
│   │   │   │                                   ← ~4000 partículas que orbitan
│   │   │   │                                   ← Bloom postprocessing (R3F)
│   │   │   │                                   ← Recibe prop `state` idle/thinking/speaking
│   │   │   │                                   ← ⚠️ NO usa model.stl — es puramente procedural
│   │   │   │                                   ← Para Next.js: migrar como Server Component con 'use client' y R3F
│   │   │   └── JarvisFace.tsx              ← Componente legacy (revisar)
│   │   │
│   │   └── store/
│   │       └── jarvisStore.ts              ← Zustand store (estado del agente: idle, thinking, speaking)
│   │
│   └── dist/                               ← Build output (⚠️ puede estar desactualizado)
│
│
# ═══════════════════════════════════════════════
# MOBILE (Expo SDK 51 + React Native)
# ANALIZAR SI MIGRAMOS A NEXT.JS (PWA) O MANTENEMOS SEPARADO
# ═══════════════════════════════════════════════
│
├── mobile/                                 ← App móvil Expo
│   ├── App.tsx                             ← NO usa expo-router: AppNavigator propio
│   ├── package.json                        ← Main: "expo-router/entry" ¿? App.tsx usa NavigationContainer
│   ├── app.json                            ← Config Expo
│   ├── babel.config.js
│   │
│   ├── src/
│   │   ├── navigation/
│   │   │   └── AppNavigator.tsx            ← Bottom tabs: Chat, Notes, Todos, Calendar, Email
│   │   ├── screens/
│   │   │   ├── AgentScreen.tsx             ← Main screen: POST /agent/run
│   │   │   ├── ChatScreen.tsx              ← WS chat o REST fallback
│   │   │   ├── NotesScreen.tsx
│   │   │   ├── NoteDetailScreen.tsx
│   │   │   ├── TodosScreen.tsx
│   │   │   ├── TodoDetail.tsx
│   │   │   ├── CalendarScreen.tsx
│   │   │   ├── CalendarEventDetail.tsx
│   │   │   ├── EmailScreen.tsx
│   │   │   ├── EmailDetailScreen.tsx
│   │   │   └── (más screens...)
│   │   ├── hooks/
│   │   │   ├── useJarvisChat.ts            ← WS hook + fallback REST
│   │   │   ├── useJarvisApi.ts             ← REST hooks (axios)
│   │   │   └── (más hooks...)
│   │   ├── api/
│   │   │   ├── jarvisApi.ts               ← Configuración de axios, baseURL
│   │   │   └── (types...)
│   │   ├── store/
│   │   │   └── jarvisStore.ts              ← Zustand con persistencia (AsyncStorage)
│   │   ├── theme/
│   │   │   └── index.ts                    ← Colors, spacing, typography, borderRadii
│   │   ├── components/
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── StreamingText.tsx
│   │   │   ├── TypingIndicator.tsx
│   │   │   ├── ActionCard.tsx
│   │   │   ├── ActionButton.tsx
│   │   │   ├── SuggestionChip.tsx
│   │   │   ├── AgentStatusBar.tsx
│   │   │   └── (más componentes UI...)
│   │
│   └── assets/                             ← Iconos, splash, fonts
│
│
# ═══════════════════════════════════════════════
# WIKI / SECOND BRAIN (Python CLI separado)
# ESTO SE QUEDA EN PYTHON (NO va a Next.js)
# ═══════════════════════════════════════════════
│
├── main.py                                 ← CLI del "Second Brain"
│   │                                         ← Obsidian vault sync, embeddings, chat CLI
│
├── knowledge_engine.py                     ← Embeddings + vector search con ChromaDB
│   │                                         ← Usa modelo "all-MiniLM-L6-v2" o similar
│
├── librarian.py                            ← Query sobre la base de conocimientos
│
├── sync_service.py                         ← KnowledgeSyncService con file watcher
│   │                                         ← Observa cambios en Obsidian vault
│
│
# ═══════════════════════════════════════════════
# SCRIPTS PYTHON Varios
# ═══════════════════════════════════════════════
│
├── check_system.py                         ← Script de verificación de sistema
├── dev_brain.py                            ← Development brain server (¿que hace?)
├── launch_brain.py                         ← Lanza cerebro standalone
├── preprocess_stl.py                       ← Preprocesa archivos STL (¿qué hace exactame nte?)
├── server_brain.py                         ← Servidor del cerebro (¿flask? ¿fastapi?)
├── server_directo.py                       ← Servidor directo (¿qué es esto?)
├── temp_list_voices.py                     ← Lista voces TTS
├── test_agent_actions.py                   ← Test de acciones del agente
├── test_agent_wiki.py                      ← Test de wiki del agente
├── test_brain_cycle.py                     ← Test del ciclo del cerebro
├── test_ollama_direct.py                   ← Test directo de Ollama
├── test_playwright.py                      ← Test con Playwright
├── verify_agent_live.py                    ← Verificación de agente en vivo
├── verify_brain.py                         ← Verificación del cerebro
├── ver_cerebro.py                          ← Visualizador del cerebro (Python + 3D?)
│
│
# ═══════════════════════════════════════════════
# CEREBRO LEGACY (HTML vanilla, versiones viejas)
# ESTO SE BORRA O ARCHIVA (NO migra a Next.js)
# ═══════════════════════════════════════════════
│
├── brain-interface/                        ← VERSIÓN VIEJA cerebro 3D (Three.js vanilla)
│   ├── index.html                          ← Cerebro 3D con OBJLoader (BrainUVs.obj, brain-andre.obj)
│   ├── start.bat                           ← Lanza server HTTP simple
│   ├── models/
│   │   ├── BrainUVs.obj                    ← Modelo OBJ (viejo)
│   │   ├── brain-andre.obj                 ← Modelo OBJ (viejo)
│   │   └── brain-parts-big_04.OBJ          ← Modelo OBJ (viejo)
│   └── textures/
│       ├── brainXRayLight.png              ← Textura X-ray
│       ├── crate.gif                       ← Textura legacy
│       ├── light.jpg/png/                  ← Texturas de luz
│       ├── spark1.png / spark2.png         ← Partículas
│       └── sky/                            ← Skybox (nx.png, ny.png, etc.)
│
├── brain_v2.html → brain_v6.html           ← Versiones legacy del cerebro HTML standalone
│   brain_v6.html = Version actual con X-Ray corregido (APRIL 2026)
│   Las demás (v2, v3, v4, v5) = desactualizadas, borrar
│
├── brain_debug.html
├── brain_final.html
├── brain_local.html
├── brain_minimal_test.html
├── brain_particulas.html
├── brain_vertices.json                     ← Datos de vertices (para test?)
│
│
# ═══════════════════════════════════════════════
# PROYECTO BASURA (ELIMINAR)
# ═══════════════════════════════════════════════
│
├── b_nU8nSrN5hHl/                          ← 🚨 PROYECTO BASURA
│   │                                         ← Next.js completo con node_modules, .next, etc.
│   │                                         ← Ocupa MEGAS. Tiene su propio package.json.
│   │                                         ← Tiene 3dbrain/ con más modelos OBJ, start.bat
│   │                                         ← Esto no es parte del proyecto JARVIS actual.
│   │                                         ← ACTION: eliminar completamente.
│
│
# ═══════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════
│
├── tests/
│   ├── phase1/                             ← Bedrock + graph basics (req. AWS)
│   ├── phase2/                             ← Tool unit tests + agent routing
│   ├── phase3/                             ← API endpoints (FastAPI)
│   └── phase4/                             ← E2E integration tests
│
│
# ═══════════════════════════════════════════════
# SCRIPTS .bat (Windows)
# ═══════════════════════════════════════════════
│
├── ABRIR_CEREBRO.bat
├── ABRIR_CEREBRO_LOCAL.bat
├── CEREBRO.bat
├── CEREBRO_DEV.bat
├── CEREBRO_DIRECTO.bat
├── CEREBRO_FINAL.bat
├── INICIAR_BACKEND.bat                     ← Activa venv, check dependencias, corre uvicorn
├── INICIAR_CEREBRO.bat                     ← Build web + inicia backend + abre browser
├── INICIAR_CEREBRO_DEV.bat
├── INICIAR_MOBILE.bat                      ← npm start en mobile/
├── INICIAR_TODO.bat                        ← Backend + web build + mobile + cerebro
├── TEST_CEREBRO.bat
├── VER_CEREBRO.bat
├── VER_CEREBRO_v2.bat
├── VER_PARTICULAS.bat
├── iniciar-mobile.bat
├── iniciar-todo.bat
│
│
# ═══════════════════════════════════════════════
# OTROS
# ═══════════════════════════════════════════════
│
├── three_local.js                          ← Three.js standalone (para brain_v6?)
├── _build_v4.py
├── _build_v5.py
├── __tree_ascii.txt
├── __tree_temp.txt
│
└── .github/workflows/ci-cd.yml             ← GitHub Actions (CI/CD)
```

---

## 3. Backend Python — Estado Detallado por Archivo

### API Layer (FastAPI)

| Archivo | Estado | Proposito | Notas |
|---------|--------|-----------|-------|
| `api/main.py` | ✅ Funcional | FastAPI app factory, routers, CORS, static files | ⚠️ Lifespan pre-warm graph crashea si LM Studio no está corriendo |
| `api/dependencies.py` | ✅ Funcional | Singleton get_jarvis_graph | — |
| `api/routers/agent.py` | ✅ Funcional | POST /agent/run | Para mobile, retorna actions + suggestions |
| `api/routers/chat.py` | ✅ Funcional | POST /chat + WS /ws/chat | Streaming con astream_events |
| `api/routers/notes.py` | ✅ Funcional | CRUD de notas | Sin auth |
| `api/routers/todos.py` | ✅ Funcional | CRUD de tareas | Sin auth |
| `api/routers/calendar.py` | ⚠️ Parcial | Google Calendar integration | Requiere OAuth token |
| `api/routers/email.py` | ⚠️ Parcial | Gmail integration | Requiere OAuth token |
| `api/routers/threads.py` | ✅ Funcional | Threads de conversación | — |
| `api/routers/messages.py` | ✅ Funcional | Mensajes dentro de threads | — |
| `api/routers/search.py` | ✅ Funcional | Semantic search con ChromaDB | Lazy import |
| `api/routers/tts.py` | ⚠️ Parcial | Text-to-speech | ¿Qué motor usa? |
| `api/routers/diagnostics.py` | ✅ Funcional | Status, health, circuit breakers | — |
| `api/routers/auth.py` | 🚧 Roto | Auth endpoints creados | NO montado en main.py. Sin uso. |

### Agente LangGraph

| Archivo | Estado | Proposito | Notas |
|---------|--------|-----------|-------|
| `agent/graph.py` | ✅ Funcional | StateGraph dinámico + tool pruning | ⚠️ MemorySaver = volátil. Necesita SqliteSaver |
| `agent/nodes.py` | ✅ Funcional | call_model, call_model_with_tools | — |
| `agent/prompts.py` | ✅ Funcional | SYSTEM_PROMPT | — |
| `agent/rag_node.py` | ✅ Funcional | retrieval_node con ChromaDB | — |
| `agent/router.py` | ✅ Funcional | Intent router | — |
| `agent/state.py` | ✅ Funcional | JarvisState TypedDict | — |

### LLM Factory

| Archivo | Estado | Proposito | Notas |
|---------|--------|-----------|-------|
| `llm/bedrock.py` | ✅ Funcional | ChatBedrock | Requiere credenciales AWS |
| `llm/lm_studio.py` | ✅ Funcional | ChatOpenAI con api_base=http://127.0.0.1:1234/v1 | Modelo hardcodeado: qwen/qwen2.5-vl-7b |
| `llm/ollama.py` | 🔴 ROTO | ChatOllama | HACK: redirige FORZOSAMENTE a lm_studio. Nunca se deshizo del fix temporal |
| `llm/__init__.py` | ✅ Funcional | Factory: get_llm(provider) | — |

### Tools

| Tool Group | Count | Estado |
|-----------|-------|--------|
| Notes | 5 | ✅ Sólido |
| Todos | 5 | ✅ Sólido |
| Calendar | 5 | ⚠️ Requiere Google OAuth |
| Email | 4 | ⚠️ Requiere Gmail OAuth |
| Web Search | 1 | ✅ Funcional (Tavily + DDG fallback) |
| Wiki | 3 | ✅ Funcional (ChromaDB) |
| Memory | 2 | ⚠️ Volátil (MemorySaver) |
| Utility | 2 | ✅ Funcional |

---

## 4. Frontend Web (React + Vite) — Estado Detallado

| Archivo | Lineas | Estado | Proposito | Migra a Next.js |
|---------|--------|--------|-----------|-----------------|
| `src/App.tsx` | 257 | ✅ Funcional | Chat UI + WebSocket + NeuralBrain | ✅ Sí, como page principal |
| `src/brain.tsx` | ~50 | ✅ Funcional | Entry point standalone cerebro | ✅ Sí, como page /brain |
| `src/main.tsx` | ~20 | ✅ Funcional | ReactDOM render | ❌ No (Next.js lo maneja) |
| `src/components/NeuralBrain.tsx` | 613 | ✅ Funcional | Cerebro 3D procedural | ✅ Sí, con 'use client' y R3F |
| `src/components/JarvisFace.tsx` | ? | 🚧 Legacy? | Probablemente otra UI | ⚠️ Revisar, posible descarte |
| `src/store/jarvisStore.ts` | ~50 | ✅ Funcional | Zustand: idle/thinking/speaking | ✅ Sí, reutilizar lógica |
| `public/` | — | ✅ | Assets sin procesar | ✅ Sí, en public/ |

### NeuralBrain.tsx (DETALLE CRÍTICO)

Este archivo es el **hero** del proyecto. Lo que hace:

1. **brainTransform()** — Función matemática que transforma puntos de una esfera en forma de cerebro (hemisferios separados, brainstem, cerebellum, gyri/sulci)
2. **ShaderMaterial custom** — Vertex + fragment shader para los "folds" orgánicos
3. **~4000 partículas** en BufferGeometry que orbitan lentamente
4. **OrbitControls** de R3F para interacción
5. **Bloom postprocessing** via @react-three/postprocessing
6. Recibe prop `state` que modifica velocidad de rotación según idle/thinking/speaking

⚠️ **Es procedural**, NO carga model.stl. El resultado es abstracto/neural, NO anatómico.

---

## 5. Mobile (Expo) — Estado Detallado

| Módulo | Estado | Notas |
|--------|--------|-------|
| App.tsx | ✅ Funcional | NavigationContainer con AppNavigator (NO expo-router a pesar de package.json) |
| AgentScreen.tsx | ✅ Funcional | Main screen: POST /agent/run, actions, suggestions |
| Navigation | ✅ Funcional | Bottom tabs (Chat, Notes, Todos, Calendar, Email) |
| Hooks (WS) | ✅ Funcional | useJarvisChat con fallback a REST |
| Zustand Store | ✅ Funcional | Persistencia via AsyncStorage |
| Theme | ✅ Funcional | Design system (colors, spacing, typography) |
| Expo SDK 51 | ✅ Funcional | Compatible con RN 0.74.5 |

**Decisión de migración:** ¿Se migra a Next.js como PWA, o se mantiene Expo separado?

**Recomendación:** Mantener Expo separado. Conectarlo al mismo backend vía API. Agregar PWA con Next.js como vía web/mobile adicional.

---

## 6. Scripts de Inicio (.bat)

| Script | Proposito | Estado |
|--------|-----------|--------|
| INICIAR_BACKEND.bat | Activa venv, instala deps, corre uvicorn | ✅ Funcional (⚠️ README dice `cd backend`, .env está en root) |
| INICIAR_CEREBRO.bat | Build web + inicia backend + abre navegador | ✅ Funcional |
| INICIAR_TODO.bat | Backend + web + mobile | ✅ Funcional |
| INICIAR_MOBILE.bat | cd mobile && npx expo start | ✅ Funcional |
| CEREBRO.bat | Abre solo el cerebro (sin backend) | ⚠️ Legacy, revisar |
| brain_v6.html | HTML standalone que carga STL con Three.js | ✅ Corregido X-Ray (29 Abr 2026) |

---

## 7. Dependencias Clave para Migración

### Python (SE MANTIENE como API)
Todos los requirements de backend se mantienen. El backend sigue corriendo como FastAPI separado.

### Next.js (NUEVO — reemplaza web/)
```json
{
  "next": "^14.x o 15.x",
  "react": "^18.2 o 19",
  "react-dom": "^18.2 o 19",
  "@react-three/fiber": "^8.15+",
  "@react-three/drei": "^9.92+",
  "@react-three/postprocessing": "^2.19+",
  "three": "^0.160.0",
  "zustand": "^5.0+",
  "tailwindcss": "^3.4+",
  "typescript": "^5.3+"
}
```

---

## 8. Problemas Conocidos / Deuda Técnica

| # | Problema | Severidad | Archivo(s) | Solución |
|---|----------|-----------|------------|----------|
| 1 | **ollama.py hackeado** — redirige a lm_studio | 🔴 Crítico | `backend/llm/ollama.py` | Implementar ChatOllama real |
| 2 | **Lifespan crashea sin LM Studio** | 🔴 Crítico | `api/main.py:52-53` | Hacer lazy load del graph |
| 3 | **MemorySaver volátil** | 🟡 Alto | `agent/graph.py` | Migrar a SqliteSaver |
| 4 | **Python 3.14 incompatible con Pydantic V1** | 🟡 Alto | Todo LangChain | Downgrade a Python 3.11-3.12 |
| 5 | **README indica `cd backend`** | 🟢 Medio | README.md | Corregir a root |
| 6 | **brain-interface/ legacy** | 🟢 Medio | Carpetas old | Eliminar o archivar |
| 7 | **brain_v2-v5.html legacy** | 🟢 Medio | Root HTMLs | Eliminar |
| 8 | **b_nU8nSrN5hHl/ basura** | 🟢 Medio | Proyecto Next.js separado | Eliminar |
| 9 | **Auth no aplica en routers** | 🟡 Alto | core/auth.py, routers/ | Montar Depends en routers |
| 10 | **API key en .env hardcodeada** | 🟡 Alto | .env (JWT_SECRET) | Generar random en producción |
| 11 | **Web build puede estar outdated** | 🟢 Medio | web/dist/ | Reconstruir al migrar |
| 12 | **Mobile apunta a localhost:8000** | 🟢 Medio | mobile/.env | Usar IP local para físico |

---

## 9. Plan de Migración a Next.js

### Decisión Arquitectónica

```
┌─────────────────────────────────────────────┐
│              FRONTEND WEB                     │
│              (Next.js App Router)           │
│                                             │
│   /              →  App principal (chat)    │
│   /brain         →  Cerebro 3D (X-Ray)      │
│   /brain/neural  →  NeuralBrain original    │
│   /notes         →  CRUD notas              │
│   /todos         →  CRUD tareas             │
│   /calendar      →  Eventos                 │
│   /emails        →  Emails                  │
│   /settings      →  Configuración           │
│                                             │
│   WebSocket en /ws/chat (client-side)       │
└──────────┬────────────────────────────────────┘
           │ REST API (fetch/axios desde browser)
           ▼
┌─────────────────────────────────────────────┐
│              BACKEND API (SE MANTIENE)      │
│              (FastAPI + LangGraph)            │
│                                             │
│   Puerto: 8000                              │
│   CORS: http://localhost:3000 (Next.js dev)   │
│                                             │
│   - AI agent                                │
│   - 23 Tools                                │
│   - SQLite                                  │
│   - WebSocket streaming                     │
│   - LLM factory (LM Studio / Ollama / Bedrock)│
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│              MOBILE (SE MANTIENE)           │
│              (Expo + React Native)            │
│                                             │
│   - Conecta al mismo FastAPI backend        │
│   - No se migra a Next.js                   │
│   - Opcional: crear PWA paralela con Next.js│
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│              WIKI (SE MANTIENE)             │
│              (Python CLI)                     │
│                                             │
│   - ChromaDB                                │
│   - Obsidian sync                           │
│   - Embeddings                              │
└─────────────────────────────────────────────┘
```

### Fases de Migración

#### Fase 0: Limpieza (Hacer primero)
1. ✅ Eliminar `b_nU8nSrN5hHl/` (basura completa)
2. ✅ Eliminar `brain_v2.html` hasta `brain_v5.html` (solo mantener v6)
3. ✅ Eliminar `brain-interface/` (o archivar azip)
4. ✅ Eliminar `brain_debug.html`, `brain_final.html`, etc. (solo dejar v6 + React components)
5. ✅ Revisar `brain_vertices.json` — ¿se usa?
6. ✅ Consolidar scripts .bat redundantes

#### Fase 1: Setup Next.js (2-3 horas)
7. Crear nueva carpeta `web-next/` con `create-next-app@latest`
8. Instalar deps: Three.js, R3F, R3P, Zustand, Tailwind
9. Configurar `next.config.js` con rewrites a localhost:8000 para CORS en dev
10. Copiar assets (`web/public/`) a `web-next/public/`

#### Fase 2: Migrar Cerebro 3D (4-6 horas)
11. **NeuralBrain.tsx** → `app/brain/neural/page.tsx` como Client Component ('use client')
    - Necesita adaptar import de R3F (Canvas, useFrame, etc.)
    - Bloom postprocessing: @react-three/postprocessing funciona igual
    - OrbitControls: @react-three/drei funciona igual
    - El componente es autocontenido, migración directa
12. **Cerebro X-Ray (model.stl, brain_v6.html)** → Nueva page `/brain`
    - Usar `@react-three/fiber` + `@react-three/drei` con `STLLoader`
    - Implementar look X-Ray con `MeshPhysicalMaterial` + `EdgesGeometry` + Bloom
    - Rotación corregida (de costado)
    - Botones de ajuste X+, X-, Y+, Y-, Z+, Z-

#### Fase 3: Migrar App Principal (4-6 horas)
13. **App.tsx** → `app/page.tsx`
    - WebSocket: `new WebSocket('ws://localhost:8000/ws/chat')` funciona igual
    - El layout chat + cerebro: usar Tailwind para layout
    - States: Zustand con persistencia opcional (localStorage)
14. **Zustand Store** → Reutilizar lógica, adaptar a Next.js si hay hidratación

#### Fase 4: Rutas Adicionales (4-6 horas)
15. `/notes` → `app/notes/page.tsx` + layout
16. `/todos` → `app/todos/page.tsx`
17. `/calendar` → `app/calendar/page.tsx`
18. `/emails` → `app/emails/page.tsx`
19. Integrar con API: fetch/axios a localhost:8000 (o configurar NEXT_PUBLIC_API_URL)

#### Fase 5: Backend Fixes (2-4 horas, paralelo)
20. Arreglar `ollama.py` (ChatOllama real)
21. Hacer lazy load del graph en lifespan
22. Cambiar MemorySaver → SqliteSaver
23. Hacer que auth funcione (montar Depends en routers)
24. Corregir README

#### Fase 6: Build y Deploy (2-3 horas)
25. Configurar `next.config.js` para export static (si se quiere hostear en FastAPI `/static`)
   O
26. Usar `npm run build` de Next.js y copiar `.next/static` + `.next/server/pages` al servidor
27. Verificar que el build funciona en producción

---

## 10. Assets del Proyecto

### Modelos 3D
| Archivo | Formato | Ubicación | Uso |
|---------|---------|-----------|-----|
| BrainUVs.obj | Wavefront OBJ | brain-interface/models/ | Legacy |
| brain-andre.obj | Wavefront OBJ | brain-interface/models/ | Legacy |
| brain-parts-big_04.OBJ | Wavefront OBJ | brain-interface/models/ | Legacy |
| model.stl | STL | C:\Users\First\Downloads\ (afuera del repo) | brain_v6.html (carga manual) |
| brain_fixed.obj | Wavefront OBJ | C:\Users\First\Downloads\ (afuera del repo) | Verificador standalone |

### Texturas
| Archivo | Ubicación | Uso |
|---------|-----------|-----|
| brainXRayLight.png | brain-interface/textures/ | X-Ray (legacy) |
| light.jpg / light.png / light2.png | brain-interface/textures/ | Iluminación legacy |
| spark1.png / spark2.png | brain-interface/textures/ | Partículas legacy |
| sky/*.png (nx ny pz py pz) | brain-interface/textures/sky/ | Skybox (legacy) |

---

## 11. Configuraciones Críticas

### .env (Raíz del proyecto)
```env
# Config actual (LM Studio)
LLM_PROVIDER=lm_studio
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
DATA_DIR=data
MAX_CONTEXT_MESSAGES=50
CORS_ORIGINS=["*"]
API_HOST=0.0.0.0
API_PORT=8000
WIKI_LLM_MODEL=local-model
TAVILY_API_KEY=tvly-...
```

### next.config.js (Para Next.js cuando se cree)
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      // En dev, proxy API requests al backend FastAPI
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ]
  },
}
module.exports = nextConfig
```

---

## 12. Decisión Final: ¿Qué va a Next.js?

| Componente | Migra a Next.js? | Nota |
|------------|-----------------|------|
| App principal (chat + cerebro) | ✅ Sí | `app/page.tsx` |
| NeuralBrain procedural | ✅ Sí | `app/brain/neural/page.tsx` |
| Cerebro X-Ray STL | ✅ Sí | `app/brain/page.tsx` (default) |
| Zustand store | ✅ Sí | Reutilizar lógica |
| WebSocket chat | ✅ Sí | Client Component con 'use client' |
| Backend FastAPI | ❌ No | Se queda como API separada |
| Mobile Expo | ❌ No | Se mantiene aparte |
| Wiki/Second Brain | ❌ No | Python CLI separado |
| MCP Server | ❌ No | Python separado |
| brain-interface/ legacy | ❌ No | Eliminar |
| brain_v*.html legacy | ❌ No | Eliminar (menos v6) |
| b_nU8nSrN5hHl/ | ❌ No | Eliminar completamente |

---

*Documento generado para preservar contexto completo antes de migración.*
*Cualquier cambio futuro debe registrar la fecha y motivo.*
