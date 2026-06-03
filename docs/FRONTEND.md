# JARVIS — Documentación del Frontend

## Stack
- **Framework**: Next.js 14 (App Router)
- **UI**: Tailwind CSS 4 + shadcn/ui
- **State**: Zustand (persist a localStorage)
- **3D**: Three.js + React Three Fiber (brain.stl)
- **Voice**: MediaRecorder API → Groq STT → Piper TTS (WebSocket)

## Estructura de archivos
```
web-next/src/
├── app/
│   ├── layout.tsx           # Root layout (metadata, fonts, ErrorBoundary)
│   ├── globals.css           # Tailwind + custom CSS animations
│   └── page.tsx              # Página principal: brain 3D + paneles + navbar
├── components/
│   ├── panels/
│   │   ├── ChatModePanel.tsx     # Chat con WS streaming + tool calls visibles
│   │   ├── NotesModePanel.tsx    # Notas: crear, listar, expandir, eliminar
│   │   ├── TasksModePanel.tsx    # Tareas: crear, completar, eliminar
│   │   ├── GmailPanel.tsx        # Bandeja, detalle, Redactar (modal)
│   │   ├── DrivePanel.tsx        # Grid/list, upload, download, delete
│   │   ├── CalendarPanel.tsx     # Calendario mensual + eventos próximos
│   │   ├── WikiPanel.tsx         # Búsqueda semántica + reindex
│   │   ├── SettingsPanel.tsx     # Configuración + health check
│   │   ├── PersonalitiesPanel.tsx # Selección de personalidad
│   │   ├── FilesModePanel.tsx    # Railway Storage (legacy, no usado)
│   │   ├── TimerModePanel.tsx    # Timer
│   │   └── VoiceModePanel.tsx    # Voz (deprecado, reemplazado por VoiceControls)
│   ├── VoiceControls.tsx     # Mic button + waveform + TTS toggle (global)
│   ├── BrainBackground.tsx   # Cerebro 3D (STL) con estados de color
│   ├── ThinkingBubble.tsx    # Burbuja de estado flotante
│   ├── AppSidebar.tsx        # Sidebar lateral (alternativa a bottom navbar)
│   ├── CommandPalette.tsx    # ⌘K command palette
│   └── ui/                   # Componentes shadcn/ui (Button, Input, Badge, etc.)
├── hooks/
│   └── useJarvisChat.ts      # WebSocket singleton global + streaming handler
├── store/
│   └── jarvisStore.ts        # Zustand store (persiste chat, pantalla, persona)
├── lib/
│   ├── api.ts                # API_BASE (auto-detecta localhost vs Railway)
│   └── utils.ts              # cn() className merger
└── brain/                    # Assets del cerebro 3D
```

## Flujo de navegación

```
┌─────────────────────────────────────────────────────┐
│  Home (Brain 3D + Voice Controls + Mic button)      │
│                                                      │
│  ┌──────┬──────┬──────┬──────┬──────┬──────┬────┐  │
│  │ Home │ Chat │Notas │Tareas│ Mail │Calen │Conf│  │
│  └──────┴──────┴──────┴──────┴──────┴──────┴────┘  │
│                  Bottom Navbar                       │
└─────────────────────────────────────────────────────┘
```

Cada panel es una vista que ocupa el área central (encima del brain 3D con blur).

## WebSocket streaming

### Conexión
- Singleton global en `useJarvisChat.ts` (ref-counting)
- Reconexión con exponential backoff (1s → 30s máx)
- Auto-detecta `wss://` vs `ws://` según API_BASE

### Eventos recibidos del backend
| Tipo | Significado | Acción |
|------|-------------|--------|
| `token` | Mensaje de estado ("Pensando...") | Muestra como indicador temporal |
| `stream` | Tokens reales del LLM | Acumula en el mensaje del asistente |
| `tool_start` | Agente va a usar una herramienta | Añade al array `toolCalls` del mensaje |
| `tool_end` | Herramienta completada | Marca el último toolCall con output |
| `done` | Respuesta completa | Quita isStreaming, activa TTS si voiceEnabled |
| `error` | Error | Muestra en rojo |

### Estados visuales en el chat
```
▸ Pensando...                          ← token (status)
⚡ create_note                         ← tool_start
✓ create_note · completado            ← tool_end
Hola, creé la nota que pediste...     ← stream (contenido real)
```

## Store Zustand (jarvisStore)
```typescript
{
  activityState: 'idle' | 'thinking' | 'speaking' | 'listening' | 'error' | 'sleep'
  currentScreen: 'home' | 'chat' | 'notes' | 'tasks' | 'gmail' | 'calendar' | 'drive' | 'wiki' | 'settings' | 'personalities'
  voiceEnabled: boolean           // TTS toggle global
  chatMessages: ChatMessage[]     // Historial con toolCalls
  persona: Persona | null
  backendStatus: 'connected' | 'disconnected' | 'error'
  lastAssistantText: string
  lastUserText: string
}
```

## Voice pipeline (frontend)
```
1. Usuario hace click en mic → MediaRecorder.start()
2. Graba audio/webm chunks
3. Usuario suelta → POST /api/v1/voice (multipart/form-data)
4. Backend: STT → LLM → TTS → response
5. Frontend recibe { transcript, response_text, audio_base64 }
6. appendChatMessage(user, transcript)
7. appendChatMessage(assistant, response_text)
8. Si audio_base64: playAudio() → navega a /chat
```

## API calls
- Todos los paneles usan `API_BASE` de `@/lib/api`
- `API_BASE` = `http://localhost:8001` en local, `https://backend-production-2522d.up.railway.app` en prod
- Next.js rewrites en `next.config.mjs`:
  - `/api/:path*` → `${API_BASE}/api/v1/:path*`
  - `/auth/:path*` → `${API_BASE}/auth/:path*`
  - `/health` → `${API_BASE}/health`
