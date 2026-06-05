'use client'

import React, { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'
import { useJarvisStore } from '@/store/jarvisStore'
import { 
  Mic, Zap, MessageCircle, BrainCircuit, Moon, AlertTriangle, 
  FolderOpen, StickyNote, CheckSquare, Settings, Sparkles, Mail, Calendar, BookOpen, LogIn, Loader2
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { API_BASE } from '@/lib/api'

/* ── Lazy-load panels + brain + bubble + voice ───────────────── */
const BrainBackground = dynamic(() => import('@/components/BrainBackground'), { ssr: false })
const ThinkingBubble  = dynamic(() => import('@/components/ThinkingBubble'),  { ssr: false })
const VoiceControls   = dynamic(() => import('@/components/VoiceControls'),   { ssr: false })

const ChatPanel        = dynamic(() => import('@/components/panels/ChatModePanel'),       { ssr: false })
const TasksPanel       = dynamic(() => import('@/components/panels/TasksModePanel'),      { ssr: false })
const NotesPanel       = dynamic(() => import('@/components/panels/NotesModePanel'),      { ssr: false })
const SettingsPanel    = dynamic(() => import('@/components/panels/SettingsPanel'),       { ssr: false })
const PersonalitiesPanel = dynamic(() => import('@/components/panels/PersonalitiesPanel'), { ssr: false })
const GmailPanel       = dynamic(() => import('@/components/panels/GmailPanel'),          { ssr: false })
const DrivePanel       = dynamic(() => import('@/components/panels/DrivePanel'),          { ssr: false })
const CalendarPanel    = dynamic(() => import('@/components/panels/CalendarPanel'),       { ssr: false })
const WikiPanel        = dynamic(() => import('@/components/panels/WikiPanel'),           { ssr: false })

const PANELS: Record<string, React.ComponentType> = {
  chat: ChatPanel, 
  notes: NotesPanel, 
  tasks: TasksPanel,
  personalities: PersonalitiesPanel,
  settings: SettingsPanel,
  gmail: GmailPanel,
  drive: DrivePanel,
  calendar: CalendarPanel,
  wiki: WikiPanel,
}

/* ── State meta for status indicator ─────────────────────────── */
const STATE_META: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  idle:      { label: 'Neural Link Active', color: '#44ccdd', icon: BrainCircuit },
  listening: { label: 'Audio Input',        color: '#00ff88', icon: Mic },
  thinking:  { label: 'Processing',         color: '#ffaa00', icon: Zap },
  speaking:  { label: 'Transmitting',       color: '#00d4ff', icon: MessageCircle },
  error:     { label: 'System Error',       color: '#ff4444', icon: AlertTriangle },
  sleep:     { label: 'Standby',            color: '#5566aa', icon: Moon },
}

/* ── Status Indicator (top-right) ────────────────────────────── */
function StatusIndicator() {
  const { activityState } = useJarvisStore()
  const meta = STATE_META[activityState] || STATE_META.idle

  return (
    <div className="fixed top-5 right-5 z-50 flex items-center gap-2 px-3.5 py-2 rounded-full"
      style={{
        background: 'rgba(0,0,0,0.25)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(255,255,255,0.05)',
      }}
    >
      <div
        className="w-2 h-2 rounded-full transition-all duration-300"
        style={{
          background: meta.color,
          boxShadow: `0 0 ${activityState === 'thinking' ? '16px' : '8px'} ${meta.color}`,
          animation: activityState === 'thinking' || activityState === 'listening' ? 'statusPulse 1.2s infinite' : 'none',
        }}
      />
      <span className="text-[10px] font-semibold text-white/50 tracking-wider">{meta.label}</span>
    </div>
  )
}

/* ── Floating Title (Home only) ────────────────────────────── */
function FloatingTitle() {
  return (
    <div className="fixed top-12 left-1/2 -translate-x-1/2 z-40 pointer-events-none text-center">
      <h1 className="text-3xl font-black tracking-[0.35em] text-white/80" style={{ textShadow: '0 0 35px rgba(68,204,221,0.25)' }}>
        JARVIS
      </h1>
      <p className="text-[9px] tracking-[0.45em] uppercase text-cyan-400/40 mt-2 font-bold">Quantum Core Active</p>
    </div>
  )
}

/* ── Unified Panel View (Blurred backdrops, header) ─────────── */
function UnifiedPanelView() {
  const { currentScreen } = useJarvisStore()
  const activeScreen = currentScreen === 'home' ? 'chat' : currentScreen
  const Panel = PANELS[activeScreen] || ChatPanel

  const titles: Record<string, string> = {
    chat: 'Chat Inteligente',
    notes: 'Notas Neurales',
    tasks: 'Tareas y Pendientes',
    files: 'Railway Storage',
    settings: 'Configuración del Sistema',
    personalities: 'Personalidades',
    gmail: 'Correo Gmail',
    drive: 'Google Drive',
    calendar: 'Google Calendar',
    wiki: 'Wiki / Obsidian',
  }

  return (
    <div className="flex flex-col w-full h-full bg-[#06060c]/80 backdrop-blur-2xl text-white">
      {/* Top Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.05] shrink-0"
        style={{
          background: 'linear-gradient(180deg, rgba(0,0,0,0.4) 0%, rgba(0,0,0,0) 100%)'
        }}
      >
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_#44ccdd]" />
          <h1 className="text-xs font-black tracking-[0.2em] uppercase text-white/85">
            {titles[activeScreen] || 'JARVIS'}
          </h1>
        </div>
        <div className="text-[8px] font-black text-cyan-300/80 tracking-widest bg-cyan-400/10 border border-cyan-400/25 px-2.5 py-1 rounded-full uppercase shadow-[0_0_12px_rgba(68,204,221,0.15)]">
          Neural Link
        </div>
      </div>
      
      {/* Content Scroll Area */}
      <div className="flex-1 overflow-y-auto pb-24 scrollbar-hide">
        <Panel />
      </div>
    </div>
  )
}

/* ── Unified Floating Bottom Navbar ────────────────────────── */
function UnifiedBottomNavbar() {
  const { currentScreen, setScreen } = useJarvisStore()
  const activeScreen = currentScreen === 'home' ? 'home' : currentScreen

  const tabs = [
    { id: 'home', label: 'Home', icon: BrainCircuit },
    { id: 'chat', label: 'Chat', icon: MessageCircle },
    { id: 'notes', label: 'Notas', icon: StickyNote },
    { id: 'tasks', label: 'Tareas', icon: CheckSquare },
    { id: 'gmail', label: 'Mail', icon: Mail },
    { id: 'calendar', label: 'Calen', icon: Calendar },
    { id: 'drive', label: 'Drive', icon: FolderOpen },
    { id: 'wiki', label: 'Wiki', icon: BookOpen },
    { id: 'personalities', label: 'Mind', icon: Sparkles },
    { id: 'settings', label: 'Conf', icon: Settings },
  ]

  return (
      <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 w-[96vw] max-w-[740px] px-2 py-2 rounded-2xl flex items-center justify-around border border-white/[0.08]"
      style={{
        background: 'rgba(7,7,12,0.8)',
        backdropFilter: 'blur(32px) saturate(1.4)',
        boxShadow: '0 -10px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06)'
      }}
    >
      {tabs.map((tab) => {
        const Icon = tab.icon
        const active = activeScreen === tab.id
        return (
          <button
            key={tab.id}
            onClick={() => setScreen(tab.id as any)}
            className={cn(
              "flex flex-col items-center gap-1.5 py-1 px-2 rounded-xl active:scale-95 transition-all text-xs relative cursor-pointer",
              active ? "text-cyan-300 font-bold" : "text-white/40 hover:text-white/70"
            )}
          >
            <Icon className={cn("w-4 h-4 transition-transform duration-300", active && "scale-110 text-cyan-300")} />
            <span className="text-[9px] tracking-wider whitespace-nowrap">{tab.label}</span>
            {active && (
              <span className="absolute bottom-0 w-3 h-0.5 bg-cyan-300 rounded-full shadow-[0_0_8px_#44ccdd]" />
            )}
          </button>
        )
      })}
    </div>
  )
}

/* ── Welcome / Google Auth Screen ──────────────────────────── */
function WelcomeScreen() {
  const { googleConnected, checkGoogleAuth } = useJarvisStore()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    checkGoogleAuth(API_BASE).finally(() => setChecking(false))
  }, [])

  if (checking) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-[#040408]">
        <Loader2 className="h-10 w-10 animate-spin text-cyan-400/60" />
        <p className="text-xs text-white/20 tracking-widest">INITIALIZING NEURAL CORE</p>
      </div>
    )
  }

  if (googleConnected) return null

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-6 p-8 bg-[#040408]">
      <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-cyan-500/20 to-violet-500/20 border border-cyan-500/30 flex items-center justify-center shadow-[0_0_60px_rgba(68,204,221,0.15)]">
        <BrainCircuit className="h-10 w-10 text-cyan-400" />
      </div>
      <div className="text-center space-y-3 max-w-sm">
        <h1 className="text-2xl font-black tracking-[0.25em] text-white/90" style={{ textShadow: '0 0 35px rgba(68,204,221,0.25)' }}>JARVIS</h1>
        <p className="text-sm text-white/50 leading-relaxed">
          Tu asistente personal con Gmail, Drive, Calendar, notas, tareas y búsqueda semántica.
        </p>
        <p className="text-xs text-white/25">Conectá tu cuenta de Google para empezar.</p>
      </div>
      <a
        href={`${API_BASE}/auth/google/login`}
        className="inline-flex items-center gap-3 px-8 py-3 bg-white text-black font-bold rounded-2xl text-sm hover:bg-white/90 transition-all hover:scale-[1.02] active:scale-[0.98] shadow-[0_0_30px_rgba(255,255,255,0.1)]"
      >
        <LogIn className="h-4 w-4" /> Conectar con Google
      </a>
      <p className="text-[10px] text-white/15 mt-2">
        Gmail · Drive · Calendar · Todo en uno
      </p>
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════
   ROOT PAGE — CINEMATIC JARVIS (ADAPTIVE VIEWPORT)
   A fully unified iOS/macOS responsive application.
╚══════════════════════════════════════════════════════════════ */
export default function RootPage() {
  const { currentScreen, googleConnected, checkGoogleAuth } = useJarvisStore()
  const activeScreen = currentScreen === 'home' ? 'home' : currentScreen

  useEffect(() => {
    checkGoogleAuth(API_BASE)
  }, [])

  const showApp = googleConnected === true

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-[#040408] text-white">
      {/* Google Auth Gate — blocks everything until connected */}
      {googleConnected !== true && <WelcomeScreen />}

      {/* 1. 3D Brain full screen background (Always active in z-0) */}
      <BrainBackground />
      
      {/* 2. Ambient backdrop overlay to adjust contrast when panels are loaded */}
      {activeScreen !== 'home' && (
        <div className="absolute inset-0 z-10 bg-black/40 backdrop-blur-sm transition-all duration-500" />
      )}

      {/* 3. Floating Status Badge */}
      {showApp && <StatusIndicator />}

      {/* 4. Thinking Bubble status block */}
      <ThinkingBubble />

      {/* 5. Main Screen Render Logic */}
      {activeScreen === 'home' ? (
        <>
          {/* Centered Large Microphone and Waves */}
          <VoiceControls />

          {/* Holographic Header */}
          <FloatingTitle />
        </>
      ) : (
        /* Floating centered viewport card for notes/tasks/chat/etc. */
        <div className="relative z-20 flex items-center justify-center w-full h-full pt-4 pb-24">
          <div className="w-full h-full md:w-[600px] md:h-[82vh] md:rounded-[28px] md:border md:border-white/[0.08] md:shadow-[0_24px_60px_rgba(0,0,0,0.6)] overflow-hidden animate-fade-in">
            <UnifiedPanelView />
          </div>
        </div>
      )}

      {/* 6. Single Unified Floating Bottom Navbar */}
      {showApp && <UnifiedBottomNavbar />}
    </div>
  )
}