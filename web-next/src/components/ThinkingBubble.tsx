'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useJarvisStore } from '@/store/jarvisStore'
import { Brain, Mic, Volume2 } from 'lucide-react'

/* ─── Thinking Bubble v3 — Compact status orb ───
   ONLY shows status label + icon. NEVER shows full response text.
   Response text stays in the chat panel where it belongs.
*/

const THINKING_LINES = [
  'Analizando patrones...',
  'Sincronizando sinapsis...',
  'Optimizando inferencia...',
  'Consultando memoria...',
  'Procesando contexto...',
]

export default function ThinkingBubble() {
  const { activityState } = useJarvisStore()
  const [show, setShow] = useState(false)
  const [label, setLabel] = useState('')
  const [subtext, setSubtext] = useState('')

  useEffect(() => {
    if (activityState === 'thinking') {
      setShow(true)
      setLabel('Pensando')
      setSubtext(THINKING_LINES[Math.floor(Math.random() * THINKING_LINES.length)])
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
  }, [activityState])

  const color = activityState === 'thinking' ? '#ec4899'
    : activityState === 'listening' ? '#00ff88'
    : activityState === 'speaking' ? '#40e0d0'
    : '#4488aa'

  const Icon = activityState === 'thinking' ? Brain
    : activityState === 'listening' ? Mic
    : activityState === 'speaking' ? Volume2
    : Brain

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="fixed left-1/2 z-40 pointer-events-none"
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
              border: '1px solid rgba(255,255,255,0.06)',
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

            {/* Pulsing icon */}
            <div className="relative w-7 h-7 flex items-center justify-center"
              style={{ color }}
            >
              <motion.div
                className="absolute inset-0 rounded-full"
                style={{ background: color }}
                animate={{ scale: [1, 1.6, 1], opacity: [0.3, 0, 0.3] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
              />
              <Icon className="w-4 h-4 relative z-10" strokeWidth={2.5} />
            </div>

            {/* Text */}
            <div className="flex flex-col">
              <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-white/60">
                {label}
              </span>
              <span className="text-[11px] text-white/30 mt-0.5">
                {subtext}
              </span>
            </div>

            {/* Dots */}
            <div className="flex gap-[3px] ml-1">
              {[0,1,2].map(i => (
                <motion.div key={i} className="w-[3px] h-[3px] rounded-full"
                  style={{ background: color }}
                  animate={{ opacity: [0.2, 1, 0.2] }}
                  transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
                />
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
