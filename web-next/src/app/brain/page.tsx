'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'
import { BrainCircuit, Mic, Zap, MessageCircle, AlertTriangle, Moon } from 'lucide-react'

const BrainVisual = dynamic(() => import('@/components/BrainVisual'), { ssr: false })

type BrainState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error' | 'sleep'

const STATE_META: Record<BrainState, { label: string; color: string; icon: any }> = {
  idle:      { label: 'Neural Link Active', color: '#44ccdd', icon: BrainCircuit },
  listening: { label: 'Audio Input',        color: '#00ff88', icon: Mic },
  thinking:  { label: 'Processing',         color: '#ffaa00', icon: Zap },
  speaking:  { label: 'Transmitting',       color: '#00d4ff', icon: MessageCircle },
  error:     { label: 'System Error',       color: '#ff4444', icon: AlertTriangle },
  sleep:     { label: 'Standby',           color: '#5566aa', icon: Moon },
}

export default function BrainStandalonePage() {
  const [state, setState] = useState<BrainState>('idle')
  const states: BrainState[] = ['idle', 'listening', 'thinking', 'speaking', 'error', 'sleep']

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-[#050510] flex flex-col items-center justify-center">
      <BrainVisual width={500} height={440} />

      <div className="absolute top-6 left-0 right-0 z-20 flex justify-center">
        <h1 className="text-xl font-bold tracking-[0.25em] text-white/70"
          style={{ textShadow: `0 0 30px ${STATE_META[state].color}40` }}>
          JARVIS
        </h1>
      </div>

      <div className="absolute bottom-10 left-0 right-0 z-20 flex justify-center">
        <div className="flex items-center gap-1.5 rounded-2xl p-1.5"
          style={{ background: 'rgba(255,255,255,0.03)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.06)' }}>
          {states.map((s) => {
            const Icon = STATE_META[s].icon
            const isActive = s === state
            return (
              <button key={s} onClick={() => setState(s)}
                className="relative px-3 py-2 rounded-xl transition-all duration-300"
                style={{
                  background: isActive ? `${STATE_META[s].color}15` : 'transparent',
                  border: isActive ? `1px solid ${STATE_META[s].color}30` : '1px solid transparent',
                }}>
                <Icon className="w-4 h-4"
                  style={{ color: isActive ? STATE_META[s].color : 'rgba(255,255,255,0.3)' }} />
              </button>
            )
          })}
        </div>
      </div>
    </main>
  )
}
