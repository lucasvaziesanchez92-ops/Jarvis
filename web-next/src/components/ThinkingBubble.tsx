'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useJarvisStore } from '@/store/jarvisStore'
import { Brain, Mic, Volume2 } from 'lucide-react'

import { PERSONALITY_THEMES } from '@/constants/colors'

/* ─── Thinking Bubble v3 — Compact status orb ───
   ONLY shows status label + icon. NEVER shows full response text.
   Response text stays in the chat panel where it belongs.
*/

const THINKING_LINES = [
  'Analizando espectro de voz...',
  'Sincronizando sinapsis...',
  'Optimizando inferencia...',
  'Buscando en base de conocimientos...',
  'Preparando ejecución de herramientas...',
  'Procesando contexto neuronal...',
  'Evaluando variables lógicas...',
]

export default function ThinkingBubble() {
  const { activityState, lastAssistantText, persona } = useJarvisStore()
  const activePersonality = persona?.name || 'profesional'
  const [show, setShow] = useState(false)
  const [label, setLabel] = useState('')
  const [subtext, setSubtext] = useState('')

  const theme = PERSONALITY_THEMES[activePersonality] || PERSONALITY_THEMES.profesional

  useEffect(() => {
    let text = ''
    if (lastAssistantText) {
      const match = lastAssistantText.match(/<thought>([\s\S]*?)<\/thought>/)
      if (match) text = match[1].trim()
    }

    let intervalId: NodeJS.Timeout;

    if (activityState === 'thinking') {
      setShow(true)
      setLabel('Pensando')
      if (text) {
        // Show the actual thought truncated to 60 chars
        setSubtext(text.length > 60 ? text.slice(0, 60) + '...' : text)
      } else {
        // Rotate random phrases every 1.5 seconds to make the wait feel dynamic
        setSubtext(THINKING_LINES[Math.floor(Math.random() * THINKING_LINES.length)])
        intervalId = setInterval(() => {
          setSubtext(THINKING_LINES[Math.floor(Math.random() * THINKING_LINES.length)])
        }, 1500)
      }
    } else if (activityState === 'listening') {
      setShow(true)
      setLabel('Escuchando')
      setSubtext('Decí algo...')
    } else if (activityState === 'speaking') {
      setShow(true)
      setLabel('Hablando')
      setSubtext('Reproduciendo voz...')
    } else {
      setShow(false)
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    }
  }, [activityState, lastAssistantText])

  const color = activityState === 'thinking' ? theme.hex
    : activityState === 'listening' ? '#00ff88'
    : activityState === 'speaking' ? theme.hex
    : theme.hex

  const Icon = activityState === 'thinking' ? Brain
    : activityState === 'listening' ? Mic
    : activityState === 'speaking' ? Volume2
    : Brain

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="fixed left-1/2 z-10 pointer-events-none"
          initial={{ opacity: 0, y: -10, x: '-50%', scale: 0.9 }}
          animate={{ opacity: 1, y: 0, x: '-50%', scale: 1 }}
          exit={{ opacity: 0, y: -8, x: '-50%', scale: 0.95 }}
          transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
          style={{ top: '16%' }}
        >
          {/* Glow */}
          <div
            className="absolute -inset-4 rounded-[32px] blur-xl opacity-30"
            style={{ background: color }}
          />

          {/* Compact orb */}
          <div
            className="relative flex items-center gap-3 rounded-[20px] px-4 py-2.5"
            style={{
              background: 'rgba(12,12,20,0.85)',
              backdropFilter: 'blur(20px) saturate(1.5)',
              border: `1px solid ${color}33`,
              boxShadow: `0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05)`,
            }}
          >
            {/* Triangle */}
            <div
              className="absolute -bottom-[7px] left-1/2 -translate-x-1/2"
              style={{
                width: 0, height: 0,
                borderLeft: '8px solid transparent',
                borderRight: '8px solid transparent',
                borderTop: '8px solid rgba(12,12,20,0.85)',
              }}
            />

            {/* Pulsing icon or audio waves */}
            <div className="relative w-7 h-7 flex items-center justify-center"
              style={{ color }}
            >
              <motion.div
                className="absolute inset-0 rounded-full"
                style={{ background: color }}
                animate={{ scale: [1, 1.6, 1], opacity: [0.3, 0, 0.3] }}
                transition={{ duration: activityState === 'speaking' ? 0.8 : 2, repeat: Infinity, ease: 'easeInOut' }}
              />
              <Icon className="w-4 h-4 relative z-10" strokeWidth={2.5} />
            </div>

            {/* Text */}
            <div className="flex flex-col">
              <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-white/60">
                {label}
              </span>
              <span className="text-[11px] text-white/30 mt-0.5 max-w-[150px] truncate">
                {subtext}
              </span>
            </div>

            {/* Dots */}
            {activityState !== 'speaking' && (
              <div className="flex gap-[3px] ml-1">
                {[0,1,2].map(i => (
                  <motion.div key={i} className="w-[3px] h-[3px] rounded-full"
                    style={{ background: color }}
                    animate={{ opacity: [0.2, 1, 0.2] }}
                    transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
                  />
                ))}
              </div>
            )}
            
            {/* Audio Waves */}
            {activityState === 'speaking' && (
              <div className="flex gap-[2px] ml-1 items-center h-4">
                {[0,1,2,3].map(i => (
                  <motion.div key={i} className="w-[3px] rounded-full"
                    style={{ background: color }}
                    animate={{ height: ['4px', '14px', '4px', '10px', '4px'] }}
                    transition={{ duration: 0.6 + (i * 0.1), repeat: Infinity, ease: 'easeInOut' }}
                  />
                ))}
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
