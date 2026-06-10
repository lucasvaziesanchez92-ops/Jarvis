import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/* ── Types ───────────────────────────────────────────────────────────── */

export type ActivityState =
  | 'idle'
  | 'thinking'
  | 'speaking'
  | 'listening'
  | 'error'
  | 'sleep'

export type PanelMode =
  | 'chat'
  | 'tasks'
  | 'notes'
  | 'voice'
  | 'timer'
  | 'email'
  | 'gmail'
  | 'drive'
  | 'calendar'
  | 'wiki'
  | 'settings'
  | 'personalities'
  | 'files'

export type AppScreen =
  | 'home'
  | 'chat'
  | 'tasks'
  | 'notes'
  | 'voice'
  | 'timer'
  | 'email'
  | 'gmail'
  | 'drive'
  | 'calendar'
  | 'wiki'
  | 'settings'
  | 'personalities'
  | 'files'

export interface Persona {
  name: string
  label: string
  description: string
  icon: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  toolCalls?: Array<{
    tool: string
    input: Record<string, unknown>
    output?: string
  }>
}

export interface ConversationSession {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: number
  updatedAt: number
}

export interface JarvisStore {
  /* ── Core state ── */
  activityState: ActivityState
  currentScreen: AppScreen
  previousScreen: AppScreen | null
  panelMode: PanelMode
  panelExpanded: boolean         // Panel completo vs minimizado
  brainMode: string
  brainRenderer: '3d' | '2d' | 'none'

  /* ── Audio / Voice ── */
  micActive: boolean             // Micrófono grabando
  voiceEnabled: boolean          // TTS activo: JARVIS habla las respuestas
  visualizerAmplitude: number    // 0.0 - 1.0 para el visualizador

  /* ── Thinking / Status ── */
  statusText: string             // Texto que aparece en la burbuja
  thinkingBubbleVisible: boolean

  /* ── Persona ── */
  persona: Persona | null
  availablePersonas: Persona[]

  /* ── Chat global (persiste entre paneles) ── */
  chatMessages: ChatMessage[]
  chatInput: string
  chatSessionId: string

  /* ── Conversation History (local save) ── */
  chatHistory: ConversationSession[]

  /* ── Live chat text for ThinkingBubble and other UI ── */
  lastAssistantText: string
  lastUserText: string

  /* ── Backend Health ── */
  backendStatus: 'disconnected' | 'connecting' | 'connected' | 'error'

  /* ── Google Auth ── */
  googleConnected: boolean | null
  googleEmail: string | null

  /* ── Actions ── */
  setActivityState: (s: ActivityState) => void
  setBrainMode: (mode: string) => void
  setBrainRenderer: (r: '3d' | '2d' | 'none') => void
  setPanelMode: (m: PanelMode) => void
  setScreen: (s: AppScreen) => void
  goBack: () => void

  togglePanelExpanded: () => void
  setPanelExpanded: (v: boolean) => void

  setMicActive: (active: boolean) => void
  setVoiceEnabled: (enabled: boolean) => void
  setVisualizerAmplitude: (amp: number) => void

  setStatusText: (text: string) => void
  showThinkingBubble: (text: string) => void
  hideThinkingBubble: () => void

  setPersona: (p: Persona) => void
  setAvailablePersonas: (ps: Persona[]) => void

  setChatMessages: (msgs: ChatMessage[]) => void
  appendChatMessage: (msg: ChatMessage) => void
  updateLastChatMessage: (updater: (last: ChatMessage) => ChatMessage) => void
  setChatInput: (text: string) => void
  setChatSessionId: (id: string) => void
  clearChat: () => void

  /* ── Conversation History Actions ── */
  newConversation: () => void
  loadConversation: (id: string) => void
  renameConversation: (id: string, title: string) => void
  deleteConversation: (id: string) => void

  setLastAssistantText: (text: string) => void
  setLastUserText: (text: string) => void

  setBackendStatus: (s: 'disconnected' | 'connecting' | 'connected' | 'error') => void

  setGoogleConnected: (connected: boolean, email?: string) => void
  checkGoogleAuth: (apiBase: string) => Promise<void>

  reset: () => void
}

function makeId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`
}

/* ── Store Instance ──────────────────────────────────────────────── */

export const useJarvisStore = create<JarvisStore>()(
  persist(
    (set, get) => ({
  /* state */
  activityState: 'idle',
  currentScreen: 'home',
  previousScreen: null,
  panelMode: 'chat',
  panelExpanded: true,
  brainMode: 'hologram',
  brainRenderer: '3d',

  micActive: false,
  voiceEnabled: false,
  visualizerAmplitude: 0,

  statusText: 'Neural Link Active',
  thinkingBubbleVisible: false,

  persona: null,
  availablePersonas: [],

  chatMessages: [],
  chatInput: '',
  chatSessionId: makeId(),
  chatHistory: [],

  lastAssistantText: '',
  lastUserText: '',

  backendStatus: 'disconnected',

  googleConnected: null,
  googleEmail: null,

  /* actions */
  setActivityState: (activityState) => {
    const texts: Record<ActivityState, string> = {
      idle: 'Neural Link Active',
      thinking: 'Processing Neural Patterns...',
      speaking: 'Transmitting Intelligence...',
      listening: 'Listening...',
      error: 'Connection Lost',
      sleep: 'Neural Core Standby',
    }
    set({ activityState, statusText: texts[activityState] })
  },

  setPanelMode: (panelMode) => set({ panelMode }),

  setScreen: (currentScreen) => set((state) => ({
    currentScreen,
    previousScreen: state.currentScreen,
  })),

  goBack: () => set((state) => ({
    currentScreen: state.previousScreen ?? 'home',
    previousScreen: null,
  })),

  togglePanelExpanded: () => set((s) => ({ panelExpanded: !s.panelExpanded })),
  setPanelExpanded: (panelExpanded) => set({ panelExpanded }),
  setBrainMode: (brainMode) => set({ brainMode }),
  setBrainRenderer: (brainRenderer) => set({ brainRenderer }),

  setMicActive: (micActive) => set({ micActive }),
  setVoiceEnabled: (voiceEnabled) => set({ voiceEnabled }),
  setVisualizerAmplitude: (visualizerAmplitude) => set({ visualizerAmplitude }),

  setStatusText: (statusText) => set({ statusText }),

  showThinkingBubble: (text) => set({ statusText: text, thinkingBubbleVisible: true }),
  hideThinkingBubble: () => set({ thinkingBubbleVisible: false }),

  setPersona: (persona) => set({ persona }),
  setAvailablePersonas: (availablePersonas) => {
    // Deduplicar por nombre
    const deduped = Array.from(new Map(availablePersonas.map(p => [p.name, p])).values())
    set({ availablePersonas: deduped })
  },

  setChatMessages: (chatMessages) => set({ chatMessages }),
  appendChatMessage: (msg) => set((state) => ({ chatMessages: [...state.chatMessages, msg] })),
  updateLastChatMessage: (updater) => set((state) => {
    const msgs = state.chatMessages
    if (msgs.length === 0) return state
    const last = msgs[msgs.length - 1]
    const updated = updater(last)
    return { chatMessages: [...msgs.slice(0, -1), updated] }
  }),
  setChatInput: (chatInput) => set({ chatInput }),
  setChatSessionId: (chatSessionId) => set({ chatSessionId }),
  clearChat: () => set((state) => {
    const msgs = state.chatMessages
    if (msgs.length > 0) {
      const title = msgs[0].content.slice(0, 40) || 'Nueva conversación'
      const session: ConversationSession = {
        id: state.chatSessionId,
        title,
        messages: msgs,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      }
      const history = [session, ...state.chatHistory.filter(h => h.id !== session.id)].slice(0, 50)
      return { chatMessages: [], chatInput: '', chatSessionId: makeId(), chatHistory: history }
    }
    return { chatMessages: [], chatInput: '', chatSessionId: makeId() }
  }),

  newConversation: () => set((state) => {
    const msgs = state.chatMessages
    if (msgs.length > 0) {
      const title = msgs[0].content.slice(0, 40) || 'Nueva conversación'
      const session: ConversationSession = {
        id: state.chatSessionId,
        title,
        messages: msgs,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      }
      const history = [session, ...state.chatHistory.filter(h => h.id !== session.id)].slice(0, 50)
      return { chatMessages: [], chatInput: '', chatSessionId: makeId(), chatHistory: history }
    }
    return { chatMessages: [], chatInput: '', chatSessionId: makeId() }
  }),
  loadConversation: (id) => set((state) => {
    const conv = state.chatHistory.find(h => h.id === id)
    if (!conv) return state
    // Guardar la conversación actual antes de cambiar
    const currentMsgs = state.chatMessages
    let history = state.chatHistory
    if (currentMsgs.length > 0) {
      const curSession: ConversationSession = {
        id: state.chatSessionId,
        title: currentMsgs[0].content.slice(0, 40) || 'Nueva conversación',
        messages: currentMsgs,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      }
      history = [curSession, ...history.filter(h => h.id !== curSession.id)].slice(0, 50)
    }
    return {
      chatSessionId: conv.id,
      chatMessages: conv.messages,
      chatHistory: history,
      chatInput: '',
    }
  }),
  renameConversation: (id, title) => set((state) => ({
    chatHistory: state.chatHistory.map(h =>
      h.id === id ? { ...h, title } : h
    ),
  })),
  deleteConversation: (id) => set((state) => ({
    chatHistory: state.chatHistory.filter(h => h.id !== id),
  })),

  setLastAssistantText: (lastAssistantText) => set({ lastAssistantText }),
  setLastUserText: (lastUserText) => set({ lastUserText }),

  setBackendStatus: (backendStatus) => set({ backendStatus }),

  setGoogleConnected: (googleConnected: boolean | null, googleEmail: string | null = null) => set({ googleConnected, googleEmail }),
  checkGoogleAuth: async (apiBase: string) => {
    try {
      const res = await fetch(`${apiBase}/auth/google/status`)
      const data = await res.json()
      set({ googleConnected: data.connected ?? false, googleEmail: data.email || null })
    } catch {
      set({ googleConnected: false, googleEmail: null })
    }
  },

  reset: () => set({
    activityState: 'idle',
    panelMode: 'chat',
    panelExpanded: true,
    micActive: false,
  voiceEnabled: true,
    visualizerAmplitude: 0,
    statusText: 'Neural Link Active',
    thinkingBubbleVisible: false,
    persona: null,
    chatMessages: [],
    chatInput: '',
    chatSessionId: makeId(),
    brainMode: 'hologram',
  }),
}),
{
  name: 'jarvis-store',
  partialize: (state) => ({
    currentScreen: state.currentScreen,
    panelMode: state.panelMode,
    panelExpanded: state.panelExpanded,
    persona: state.persona,
    chatSessionId: state.chatSessionId,
    voiceEnabled: state.voiceEnabled,
    brainMode: state.brainMode,
    brainRenderer: state.brainRenderer,
    chatHistory: state.chatHistory,
  }),
}
)
)