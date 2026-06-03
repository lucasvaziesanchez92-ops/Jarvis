# PRD #2 — FRONTEND: NEXT.JS APP
## Proyecto: JARVIS | Stack: Next.js 14 + TypeScript + Tailwind + Zustand
### Versión: 1.0

---

## 1. VISIÓN DEL PRODUCTO

El frontend de Jarvis es una **Single Page Application** en Next.js que se conecta al backend FastAPI via WebSocket. La experiencia es un terminal/console futurista con un cerebro neural 3D animado en la parte superior. El usuario escribe mensajes y recibe respuestas en tiempo real con streaming de tokens.

**Referencia directa de código:**
- `web-next/src/app/page.tsx` — Chat principal con WebSocket
- `web-next/src/store/jarvisStore.ts` — Zustand state
- `web-next/src/components/NeuralBrain.tsx` — Cerebro 3D animado
- `web-next/tailwind.config.mjs` — Colores custom del tema Jarvis

---

## 2. IDENTIDAD VISUAL

### 2.1 Tema oscuro (Jarvis aesthetic)

Colores definidos en `tailwind.config.mjs`:

| Variable | Hex | Uso |
|---|---|---|
| `jarvis-dark` | `#0a0a0f` | Fondo principal |
| `jarvis-cyan` | `#00d4ff` | Acento primario, texto highlight |
| `jarvis-blue` | `#0066cc` | Botones, gradientes |
| `jarvis-green` | `#00ff88` | Confirmaciones, éxito |
| `jarvis-border` | `#1a1a2e` | Bordes sutiles |
| `jarvis-yellow` | `#ffcc00` | Warnings |
| `jarvis-red` | `#ff4444` | Errores |

### 2.2 Tipografía

- **Font principal:** System monospace (JetBrains Mono fallback)
- Chat usa: `font-mono`
- Headings: tracking-widest uppercase

### 2.3 Aesthetic

- **Referencia:** Iron Man JARVIS interface — oscuro, metálico, con acentos cyan
- ** Fondo principal:** Negro profundo con gradientes sutiles
- **Cards:** `bg-black/60` con bordes `border-jarvis-border/60`
- **Sin bordes redondeados comunes** — más bien bordes afilados o ligeramente angulados

---

## 3. ESTRUCTURA DE PÁGINAS

### 3.1 Pages existentes

```
/                    → Chat principal (page.tsx)
/brain               → X-Ray 3D viewer (brain/page.tsx)
/brain/neural        → NeuralBrain procedural (brain/neural/page.tsx)
/notes               → Lista de notas (notes/page.tsx)
/todos               → Lista de tareas (todos/page.tsx)
/calendar            → Calendario (calendar/page.tsx)
/emails              → Emails (emails/page.tsx)
```

### 3.2 Layout principal

**Header (50vh):** NeuralBrain 3D animado
- Muestra estado visual: idle (azul tenue), thinking (pulso cyan), speaking (brillo verde)
- Barra inferior con: connection status, agent state, session ID

**Body (50vh):** Chat interface
- Lista de mensajes con scroll
- Input fijo abajo con textarea

---

## 4. COMPONENTES PRINCIPALES

### 4.1 NeuralBrain (3D Brain Visualizer)

**Ubicación:** `web-next/src/components/NeuralBrain.tsx`

**Props:**
```typescript
interface NeuralBrainProps {
  state: 'idle' | 'thinking' | 'speaking'
}
```

**Rendering:**
- Usa Three.js con React Three Fiber
- `dynamic(() => import(...), { ssr: false })` para evitar window is not defined
- Modelo: `brain_fixed.obj` en `/public/`
- Partículas procedurales para efecto neural

**Estados visuales:**
- `idle`: azul tenue, partículas lentas
- `thinking`: pulso cyan, partículas aceleradas
- `speaking`: brillo verde, partículas activas con glow

**Build warning:** `Cannot find module 'three/examples/jsm/loaders/OBJLoader'` — funciona via `(THREE as any).OBJLoader`

---

### 4.2 ChatInterface (page.tsx)

**WebSocket Connection:**
```typescript
const wsUrl = 'ws://localhost:8000/ws/chat'
```

**Protocolo de mensajes:**
```typescript
// Cliente → Servidor
{ "message": "...", "session_id": "..." }

// Servidor → Cliente
{ "type": "token", "content": "..." }
{ "type": "tool_start", "tool_name": "...", "tool_input": {...} }
{ "type": "tool_end", "tool_name": "...", "tool_output": {...} }
{ "type": "done" }
{ "type": "error", "content": "..." }
```

**UI de mensajes:**
- User messages: alineados derecha, gradiente azul, `rounded-br-sm`
- Jarvis messages: alineados izquierda, fondo negro, `rounded-bl-sm`
- Tool calls visibles como: `⚡ tool_name ✓`
- Streaming: cursor `▋` animado al final del mensaje

**Input:**
- Textarea con Enter para enviar, Shift+Enter para newline
- Botón send deshabilitado si no está connected o input vacío

---

### 4.3 JarvisStore (Zustand)

```typescript
type JarvisState = 'idle' | 'thinking' | 'speaking'

interface JarvisStore {
  state: JarvisState
  message: string
  setState: (state: JarvisState) => void
  setMessage: (message: string) => void
  reset: () => void
}
```

---

## 5. PÁGINA: BRAIN VIEWER

### 5.1 /brain — X-Ray 3D Viewer

**Ubicación:** `web-next/src/app/brain/page.tsx`

**Features:**
- Carga `brain_fixed.obj` con Three.js
- Controles orbitales para rotar/zoom
- Wireframe overlay toggle
- Fullscreen toggle

### 5.2 /brain/neural — Procedural Neural Brain

**Ubicación:** `web-next/src/app/brain/neural/page.tsx`

**Features:**
- Partículas que forman un cerebro procedural
- Animación continua
- Interacción mouse para rotar

---

## 6. PÁGINAS: NOTES / TODOS / CALENDAR / EMAILS

Estas páginas son shells que se conectan a los endpoints del backend:

### 6.1 /notes
- Lista de notas del usuario
- Crear/editar/eliminar notas
- Tags en cada nota

### 6.2 /todos
- Lista de tareas
- Toggle complete
- Filter: all / active / completed
- Priority: low / medium / high

### 6.3 /calendar
- Vista mensual de eventos
- Crear/editar eventos
- Sincroniza con Google Calendar (future)

### 6.4 /emails
- Lista de emails (Gmail sync)
- Ver email completo
- Enviar email nuevo

---

## 7. CONFIGURACIÓN DE TAILWIND

### 7.1 Custom theme (tailwind.config.mjs)

```javascript
theme: {
  extend: {
    colors: {
      'jarvis-dark': '#0a0a0f',
      'jarvis-cyan': '#00d4ff',
      'jarvis-blue': '#0066cc',
      'jarvis-green': '#00ff88',
      'jarvis-border': '#1a1a2e',
      'jarvis-yellow': '#ffcc00',
      'jarvis-red': '#ff4444',
    },
  },
}
```

### 7.2 Global styles (globals.css)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: 0 0% 4%;
  --foreground: 0 0% 95%;
}
```

---

## 8. PROXY DE API (next.config.mjs)

```javascript
async rewrites() {
  return [{
    source: '/api/:path*',
    destination: 'http://localhost:8000/api/:path*',
  }]
}
```

El WebSocket NO se proxy-iza — conecta directo a `ws://localhost:8000/ws/chat` (Next.js rewrites no soportan `ws://`).

---

## 9. IMPORTACIONES CLAVE

```typescript
// Three.js para NeuralBrain (ssr: false)
import dynamic from 'next/dynamic'

// Zustand store
import { useJarvisStore } from '@/store/jarvisStore'

// cn() utility (classname helper)
import { cn } from '@/lib/utils'
```

---

## 10. DEPENDENCIAS

```json
{
  "next": "^14.0.0",
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "typescript": "^5.0.0",
  "tailwindcss": "^3.4.0",
  "@react-three/fiber": "^8.15.0",
  "@react-three/drei": "^9.88.0",
  "three": "^0.160.0",
  "zustand": "^4.4.0",
  "clsx": "^2.0.0",
  "tailwind-merge": "^2.0.0",
  "lucide-react": "^0.294.0"
}
```

---

## 11. BUILD Y DESARROLLO

```bash
cd web-next
npm install
npm run dev      # desarrollo en localhost:3000
npm run build    # producción
```

Build output: `.next/` con 10+ páginas estáticas

---

## 12. PRÓXIMOS PASOS

1. [ ] Implementar Command Palette (Cmd+K) para navegación
2. [ ] Agregar свет theme (modo claro)
3. [ ] Implementar notifications/toasts para errores
4. [ ] Agregar skeleton loading states
5. [ ] PWA support para instalable en desktop