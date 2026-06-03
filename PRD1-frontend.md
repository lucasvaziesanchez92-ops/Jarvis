# PRD 1: Jarvis Frontend (Mobile App)

> **Technology Stack**: React Native (Expo SDK 51) + TypeScript  
> **Base Directory**: `mobile/`  
> **Status**: Phase 4 — Core structure exists, needs enhancement  
> **Backend Connection**: FastAPI at `http://localhost:8000` (configurable via `EXPO_PUBLIC_API_URL`)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Current State Analysis](#2-current-state-analysis)
3. [Module Specifications](#3-module-specifications)
4. [New Modules to Implement](#4-new-modules-to-implement)
5. [State Management Strategy](#5-state-management-strategy)
6. [API Integration Patterns](#6-api-integration-patterns)
7. [UI/UX Design System](#7-uiux-design-system)
8. [Implementation Roadmap](#8-implementation-roadmap)

---

## 1. Architecture Overview

### High-Level Structure

```
┌─────────────────────────────────────────────┐
│              Mobile App (Expo)              │
├─────────────────────────────────────────────┤
│  Navigation: Bottom Tabs (5 tabs)           │
│  ├── Chat       ├── Notes       ├── Todos   │
│  └── Calendar   └── Email                    │
├─────────────────────────────────────────────┤
│  Data Layer                                  │
│  ├── REST API (axios) ←→ FastAPI backend    │
│  └── WebSocket (/ws/chat) ←→ LangGraph      │
├─────────────────────────────────────────────┤
│  State: React Hooks (no global store)       │
│  ├── useJarvisChat()    — streaming chat    │
│  ├── useNotes()         — CRUD notes        │
│  ├── useTodos()         — CRUD todos         │
│  └── useCalendar()      — CRUD events       │
└─────────────────────────────────────────────┘
```

### Key Files Map

| File | Absolute Path | Purpose |
|------|--------------|---------|
| Entry Point | `mobile/App.tsx` | SafeAreaProvider + StatusBar + AppNavigator |
| Navigation | `mobile/src/navigation/AppNavigator.tsx` | Bottom tab navigator with 5 tabs |
| API Client | `mobile/src/api/client.ts` | Axios instance + WebSocket URL derivation |
| Types | `mobile/src/api/types.ts` | TypeScript interfaces mirroring Pydantic models |
| Chat Hook | `mobile/src/hooks/useJarvisChat.ts` | WebSocket streaming, tool correlation |
| API Hook | `mobile/src/hooks/useJarvisApi.ts` | Generic CRUD + specialized hooks |
| Chat Screen | `mobile/src/screens/ChatScreen.tsx` | Message list + streaming + add-as-todo |
| Notes Screen | `mobile/src/screens/NotesScreen.tsx` | Note cards with tags |
| Todos Screen | `mobile/src/screens/TodosScreen.tsx` | Interactive todo list with modals |
| Calendar Screen | `mobile/src/screens/CalendarScreen.tsx` | Event cards |
| Email Screen | `mobile/src/screens/EmailScreen.tsx` | Email list (read-only currently) |
| MessageBubble | `mobile/src/components/MessageBubble.tsx` | Three-mode message rendering |
| TodoListRenderer | `mobile/src/components/TodoListRenderer.tsx` | Parses checkbox todos from text |
| StreamingText | `mobile/src/components/StreamingText.tsx` | Blinking cursor effect |
| TypingIndicator | `mobile/src/components/TypingIndicator.tsx` | Animated dots |

---

## 2. Current State Analysis

### What Works Well

- **WebSocket Streaming**: Real-time token-by-token response with tool start/end visualization
- **Tool Correlation**: Maps tool_name → human-readable icons and messages
- **Todo List Renderer**: Parses `- [ ]` / `- [x]` patterns from AI responses into interactive checkboxes
- **Hook Architecture**: Clean separation of API concerns via `useCollection<T>` generic
- **iOS Design Language**: Consistent color palette (#007AFF blue, proper grays, priority dots)

### What Needs Improvement

1. **Chat**: No session management UI, no message actions (copy/share/regenerate), no error retry
2. **Notes**: No detail view, no search/filter, no create/edit UI (relies on AI only)
3. **Calendar**: No event creation/editing UI, no date picker integration
4. **Email**: Read-only, no detail view, no compose/reply, no label management
5. **No Settings**: Cannot change LLM provider, model, or API URL from the app
6. **No Dashboard**: No overview of today's tasks, upcoming events, or quick actions
7. **No Global Search**: Cannot search across all data types

---

## 3. Module Specifications

### 3.1 Chat Module

**Current File**: `mobile/src/screens/ChatScreen.tsx`  
**Hook**: `useJarvisChat(sessionId?)`

**Current Features**:
- FlatList of MessageBubble components
- WebSocket streaming with token/tool_start/tool_end/done/error chunks
- Long-press assistant message → "Add as Todo"
- Auto-scroll to bottom
- Connection status indicator

**Enhancements to Add**:

| Feature | Description | Priority |
|---------|-------------|----------|
| Session Management | UI to view/select past conversation sessions | High |
| Message Actions | Copy, share, regenerate response via context menu | High |
| Error Retry | Retry button when WebSocket errors occur | High |
| Image Attachment | Send images for multimodal LLM processing | Medium |
| Voice Input | Speech-to-text integration | Medium |
| Quick Prompts | Pre-built prompt buttons (e.g., "Summarize my day") | Low |
| Offline Queue | Queue messages when disconnected, send on reconnect | Low |

**Data Flow**:
```
User types → sendMessage(text)
  → Creates UserMessage (role: "user")
  → Creates empty AssistantMessage (role: "assistant", isStreaming: true)
  → Sends { message, session_id } via WebSocket
  ← Receives StreamChunk frames:
     - "token": appends content to streaming message
     - "tool_start": creates system message "📋 Creating todo..."
     - "tool_end": updates to "✅ Todo created: ..."
     - "done": stops streaming
     - "error": shows error message
```

### 3.2 Notes Module

**Current File**: `mobile/src/screens/NotesScreen.tsx`  
**Hook**: `useNotes()` → wraps `useCollection<Note>("/notes")`

**Current Features**:
- List notes as cards with title, content (2-line truncation), tag chips
- Long-press → delete confirmation
- Loading spinner + empty state

**Enhancements to Add**:

| Feature | Description | Priority |
|---------|-------------|----------|
| Note Detail View | Tap note → full-screen view with complete content | High |
| Create Note UI | FAB button → modal with title, content, tags inputs | High |
| Edit Note | In-detail edit mode with save/cancel | High |
| Search Notes | Search bar filtering by title, content, tags | High |
| Sort Options | Sort by date created, updated, title | Medium |
| Rich Text | Bold, italic, lists, links in note content | Medium |
| Note Sharing | Share note as text/image/PDF | Low |
| Archive | Soft-delete with archive view | Low |

### 3.3 Todos Module

**Current File**: `mobile/src/screens/TodosScreen.tsx`  
**Hook**: `useTodos()` — extends useCollection with complete(), update()

**Current Features** (most complete screen):
- Priority dots (red/orange/green)
- Tap to complete
- Long-press → edit modal with text, priority, date picker
- Create modal with all fields
- Completed items shown with strikethrough + reduced opacity

**Enhancements to Add**:

| Feature | Description | Priority |
|---------|-------------|----------|
| Due Date Notifications | Push notifications when due date approaches | High |
| Categories/Projects | Group todos by project or context | High |
| Recurring Tasks | Daily/weekly/monthly recurring todos | Medium |
| Subtasks | Nested todos under parent | Medium |
| Drag Reorder | Reorder todos via drag-and-drop | Low |
| Smart Filters | "Today", "Upcoming", "Overdue", "High Priority" | Medium |

### 3.4 Calendar Module

**Current File**: `mobile/src/screens/CalendarScreen.tsx`  
**Hook**: `useCalendar()` → wraps `useCollection<CalendarEvent>("/calendar")`

**Current Features**:
- Event cards with blue accent bar, title, formatted date/time
- Long-press → delete confirmation
- Shows location and description

**Enhancements to Add**:

| Feature | Description | Priority |
|---------|-------------|----------|
| Event Creation UI | Form with title, start/end datetime, location, description | High |
| Event Edit UI | Pre-filled form for editing existing events | High |
| Day/Week View | Calendar grid showing events by time slot | High |
| Device Calendar Sync | Read/write to phone's native calendar | Medium |
| Event Reminders | Push notifications before events | Medium |
| Month View | Calendar month overview with dot indicators | Low |

### 3.5 Email Module

**Current File**: `mobile/src/screens/EmailScreen.tsx`  
**Hook**: None — manages own state with useState + apiClient

**Current Features**:
- Email list with sender, date, subject, snippet
- Loading/error/empty states
- Read-only (no actions)

**Enhancements to Add**:

| Feature | Description | Priority |
|---------|-------------|----------|
| Email Detail View | Tap email → full content with HTML rendering | High |
| Compose Email | Form with to, cc, bcc, subject, body | High |
| Reply/Forward | Reply to sender or forward email | High |
| Read/Unread Toggle | Mark emails as read/unread | High |
| Labels/Folders | View emails by Gmail labels | Medium |
| Search Emails | Use backend search_emails endpoint | Medium |
| Attachments | View/download email attachments | Low |

---

## 4. New Modules to Implement

### 4.1 Settings Module (NEW)

**File**: `mobile/src/screens/SettingsScreen.tsx`

**Purpose**: Allow users to configure the app and backend connection from the mobile device.

**Sections**:

| Setting | Type | Description |
|---------|------|-------------|
| LLM Provider | Toggle | "Ollama" ↔ "AWS Bedrock" |
| Model Name | Text Input | e.g., "llama3.2" or "claude-sonnet-4-5" |
| API URL | Text Input | Backend URL (default: http://localhost:8000) |
| Ollama Base URL | Text Input | (default: http://localhost:11434) |
| Session ID | Text Input | Custom session identifier |
| Theme | Segmented Control | Light / Dark / System |
| Clear Cache | Button | Clear local cache |
| About | Text | App version, build info |

**Implementation**: Store settings in `AsyncStorage` and sync with backend via `POST /settings` (if endpoint exists).

**Navigation**: Add gear icon as 6th tab or in a header menu.

### 4.2 Dashboard Module (NEW)

**File**: `mobile/src/screens/DashboardScreen.tsx`

**Purpose**: Home screen overview of the user's assistant data.

**Widgets**:

```
┌─────────────────────────────────┐
│  🌅 Good morning, [User]        │
├─────────────────────────────────┤
│  📋 Today's Tasks (3/7 done)    │
│  ├─ [x] Review pull request     │
│  ├─ [ ] Write documentation     │
│  └─ [ ] Team meeting at 2pm     │
├─────────────────────────────────┤
│  📅 Upcoming Events             │
│  ├─ Team Standup — 10:00 AM     │
│  └─ Doctor Appointment — 3:00pm │
├─────────────────────────────────┤
│  📝 Recent Notes                │
│  ├─ Meeting notes from Monday   │
│  └─ Project ideas               │
├─────────────────────────────────┤
│  ⚡ Quick Actions               │
│  [Create Note] [Add Todo]       │
│  [Schedule Event] [Send Email]  │
└─────────────────────────────────┘
```

**Data Sources**: 
- Todos: `GET /todos?show_completed=false`
- Calendar: `GET /calendar?upcoming_only=true`
- Notes: `GET /notes` (limit 3)

### 4.3 Global Search Module (NEW)

**File**: `mobile/src/screens/SearchScreen.tsx`

**Purpose**: Unified search across all data types.

**Features**:
- Single search input
- Results grouped by type: Notes, Todos, Calendar Events, Emails
- Debounced search (300ms)
- Recent searches stored locally
- Tap result → navigate to detail view

---

## 5. State Management Strategy

### Current Approach: React Hooks

The app currently uses React hooks without a global state library. This works well for the current scope but needs enhancement.

### Recommended Evolution

| Stage | Approach | When to Adopt |
|-------|----------|---------------|
| Current | React hooks (useState, useEffect) | ✅ Already in use |
| Phase 5 | React Context + useReducer | When Settings module needs global config |
| Phase 6 | Zustand (lightweight) | When cross-screen state sharing grows |

### Hook Architecture (Enhanced)

```
src/hooks/
├── useJarvisChat.ts        — WebSocket streaming (keep as-is)
├── useJarvisApi.ts         — Generic CRUD (keep as-is)
├── useSettings.ts          — NEW: Read/write app settings from AsyncStorage
├── useDashboard.ts         — NEW: Aggregate data from multiple endpoints
├── useSearch.ts            — NEW: Debounced multi-domain search
└── useNotifications.ts     — NEW: Push notification registration/handling
```

---

## 6. API Integration Patterns

### REST Client

**File**: `mobile/src/api/client.ts`

```typescript
// Current pattern (keep):
const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";
const WS_URL = API_URL.replace(/^http/, "ws");

// Add for enhanced error handling:
const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// Response interceptor for error handling:
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Navigate to auth/login
    }
    if (error.code === "ECONNABORTED") {
      // Show timeout message
    }
    return Promise.reject(error);
  }
);
```

### WebSocket Protocol

**Current Protocol** (from `architecture.md`):

```
Client → Server:  { "message": str, "session_id": str }
Server → Client:  { "type": "token",      "content": str }
Server → Client:  { "type": "tool_start", "tool_name": str, "tool_input": {} }
Server → Client:  { "type": "tool_end",   "tool_name": str, "tool_output": {} }
Server → Client:  { "type": "done",       "content": "" }
Server → Client:  { "type": "error",      "content": str }
```

### Error Handling Patterns

| Error Type | Frontend Behavior |
|------------|-------------------|
| WebSocket disconnect | Show "Reconnecting..." indicator, auto-retry |
| 400 Bad Request | Show validation error from `detail` field |
| 404 Not Found | Show "Not found" empty state |
| 500 Server Error | Show "Something went wrong" with retry |
| 503 Service Unavailable | Show "Service unavailable — Gmail not configured" |
| Network timeout | Show "Connection timed out" with retry |

---

## 7. UI/UX Design System

### Color Palette (iOS-Inspired)

| Name | Hex | Usage |
|------|-----|-------|
| iOS Blue | `#007AFF` | Primary actions, user bubbles, active tabs |
| System Red | `#FF3B30` | Destructive actions, errors, high priority |
| System Orange | `#FF9500` | Medium priority, warnings |
| System Green | `#34C759` | Success, checkmarks, low priority |
| System Gray | `#8E8E93` | Disabled text, secondary info, inactive tabs |
| Dark Gray | `#1C1C1E` | Primary text |
| Medium Gray | `#3C3C43` | Secondary text |
| Light Gray BG | `#F2F2F7` | Screen backgrounds, AI bubbles |
| Border Gray | `#C6C6C8` | Tab bar border, input borders |
| Input BG | `#E5E5EA` | Input field backgrounds |
| Light Blue | `#E8F4FD` | System message backgrounds |
| Tag Blue | `#E5F0FF` | Note tag backgrounds |

### Component Patterns

```typescript
// Card Pattern:
{
  borderRadius: 12,
  backgroundColor: "#FFFFFF",
  padding: 16,
  marginBottom: 12,
  // Optional shadow:
  shadowColor: "#000",
  shadowOpacity: 0.1,
  shadowRadius: 4,
}

// Button Pattern:
{
  borderRadius: 10,
  backgroundColor: "#007AFF",
  paddingVertical: 12,
  paddingHorizontal: 20,
}

// Empty State Pattern:
{
  textAlign: "center",
  color: "#8E8E93",
  fontSize: 16,
  marginTop: 40,
}
```

### Dark Mode Support

When implementing dark mode, map colors:

| Light | Dark |
|-------|------|
| `#F2F2F7` (bg) | `#1C1C1E` (bg) |
| `#FFFFFF` (card) | `#2C2C2E` (card) |
| `#1C1C1E` (text) | `#FFFFFF` (text) |
| `#8E8E93` (secondary) | `#98989D` (secondary) |

---

## 8. Implementation Roadmap

### Phase 4.1: Enhancement (Current Priority)

| Task | Files Affected | Effort |
|------|---------------|--------|
| Note Detail View | New `NoteDetailScreen.tsx`, navigation update | Medium |
| Create Note UI | `NotesScreen.tsx` modal addition | Small |
| Event Creation UI | `CalendarScreen.tsx` modal addition | Medium |
| Email Detail View | New `EmailDetailScreen.tsx`, navigation update | Medium |
| Compose Email | New `ComposeEmailScreen.tsx` | Medium |
| Settings Screen | New `SettingsScreen.tsx`, `useSettings.ts` hook | Medium |

### Phase 4.2: Features

| Task | Files Affected | Effort |
|------|---------------|--------|
| Dashboard Screen | New `DashboardScreen.tsx`, `useDashboard.ts` hook | Large |
| Global Search | New `SearchScreen.tsx`, `useSearch.ts` hook | Medium |
| Due Date Notifications | Expo Notifications integration | Medium |
| Event Edit UI | Update `CalendarScreen.tsx` | Small |
| Reply/Forward Email | Update `EmailDetailScreen.tsx` | Medium |

### Phase 4.3: Polish

| Task | Files Affected | Effort |
|------|---------------|--------|
| Dark Mode | Theme context, color mappings | Medium |
| Offline Support | NetInfo + local caching | Large |
| Voice Input | Expo Speech-to-Text | Medium |
| Image Attachments | Expo Image Picker + multipart upload | Medium |
| Push Notifications | Firebase Cloud Messaging integration | Large |

---

## References

- **React Navigation Docs**: https://reactnavigation.org/docs/getting-started
- **Expo SDK**: https://docs.expo.dev/
- **React Native Components**: https://reactnative.dev/docs/components-and-apis
- **Axios Interceptors**: https://axios-http.com/docs/interceptors
- **WebSocket in React Native**: https://reactnative.dev/docs/network#websocket
