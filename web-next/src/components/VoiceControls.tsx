'use client'

import { useRef, useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Square, Volume2, VolumeX, X } from 'lucide-react'
import { useJarvisStore } from '@/store/jarvisStore'
import { speak as ttsSpeak, stop as ttsStop, onTTSEvent } from '@/lib/tts'

const API = '/api'

export default function VoiceControls() {
  const {
    activityState, setActivityState, setMicActive, micActive,
    visualizerAmplitude, voiceEnabled, setVoiceEnabled, currentScreen,
    appendChatMessage, setLastUserText, setLastAssistantText, setScreen,
  } = useJarvisStore()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)
  const [hoveredBtn, setHoveredBtn] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const isCancelledRef = useRef<boolean>(false)

  // Sync activity state with TTS events (so the UI shows
  // 'speaking' even when Web Speech API is the one playing).
  useEffect(() => {
    const off = onTTSEvent((e) => {
      if (e.type === 'start') {
        setActivityState('speaking')
      } else if (e.type === 'end' || e.type === 'error') {
        setActivityState('idle')
      }
    })
    return () => off()
  }, [setActivityState])
  const chunksRef = useRef<Blob[]>([])
  const audioElRef = useRef<HTMLAudioElement | null>(null)
  const transcriptRef = useRef('')
  const responseRef = useRef('')

  function makeId(): string {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID()
    }
    return `vc_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`
  }

  /* ── Voice waveform canvas ────────────────────────────────── */
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const resize = () => {
      canvas.width = 400 * dpr
      canvas.height = 120 * dpr
      canvas.style.width = '400px'
      canvas.style.height = '120px'
      ctx.scale(dpr, dpr)
    }
    resize()
    window.addEventListener('resize', resize)

    const bars = 64
    const barArray = new Float32Array(bars)
    let phase = 0

    const render = () => {
      const w = 400
      const h = 120
      const isListening = activityState === 'listening'
      const isSpeaking = activityState === 'speaking'
      const amp = visualizerAmplitude || (isListening ? 0.8 : isSpeaking ? 0.5 : 0.05)

      ctx.clearRect(0, 0, w, h)

      for (let i = 0; i < bars; i++) {
        const target = amp * (
          Math.sin(phase + i * 0.3) * 0.3 +
          Math.sin(phase * 1.5 + i * 0.7) * 0.2 +
          (Math.random() - 0.5) * 0.15
        )
        barArray[i] += (target - barArray[i]) * 0.15
      }
      phase += 0.04

      const barW = w / bars
      const cx = w / 2

      ctx.lineWidth = 2
      ctx.lineCap = 'round'

      for (let i = 0; i < bars; i++) {
        const val = Math.max(0, barArray[i])
        const x = i * barW + barW / 2
        const dist = Math.abs(x - cx) / cx
        const falloff = 1 - dist * 0.6
        const height = val * falloff * h * 0.9

        if (height <= 1) continue

        const hue = isListening ? 160 : isSpeaking ? 190 : 330
        const sat = isListening ? '90%' : isSpeaking ? '80%' : '60%'
        const lit = isListening ? '65%' : isSpeaking ? '70%' : '55%'
        const alpha = 0.3 + falloff * 0.7

        ctx.strokeStyle = `hsla(${hue}, ${sat}, ${lit}, ${alpha})`
        ctx.beginPath()
        ctx.moveTo(x, h / 2 - height / 2)
        ctx.lineTo(x, h / 2 + height / 2)
        ctx.stroke()

        if (height > h * 0.15) {
          ctx.strokeStyle = `hsla(${hue}, ${sat}, ${lit}, ${alpha * 0.3})`
          ctx.beginPath()
          ctx.moveTo(x - 2, h / 2 - height / 2 * 0.7)
          ctx.lineTo(x - 2, h / 2 + height / 2 * 0.7)
          ctx.stroke()
        }
      }

      animRef.current = requestAnimationFrame(render)
    }

    render()
    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('resize', resize)
    }
  }, [activityState, visualizerAmplitude])

  /* ── Cancelar TODO ────────────────────────────────────────── */
  const cancelEverything = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.ondataavailable = null
      mediaRecorderRef.current.onstop = null
      mediaRecorderRef.current.stop()
    }
    mediaRecorderRef.current = null
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
    chunksRef.current = []

    if (audioElRef.current) {
      audioElRef.current.onended = null
      audioElRef.current.onerror = null
      audioElRef.current.pause()
      audioElRef.current.src = ''
      audioElRef.current.load()
      audioElRef.current = null
    }

    window.speechSynthesis?.cancel()

    setMicActive(false)
    setActivityState('idle')
  }, [setMicActive, setActivityState])

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach(t => t.stop())
      if (audioElRef.current) {
        audioElRef.current.pause()
        audioElRef.current.src = ''
        audioElRef.current.load()
      }
    }
  }, [])

  /* ── Recording logic ──────────────────────────────────────── */
  const startRecording = useCallback(async () => {
    try {
      if (audioElRef.current) {
        audioElRef.current.onended = null
        audioElRef.current.onerror = null
        audioElRef.current.pause()
        audioElRef.current.src = ''
        audioElRef.current.load()
        audioElRef.current = null
      }
      window.speechSynthesis?.cancel()
      setActivityState('idle')

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      chunksRef.current = []
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        streamRef.current = null
        if (!isCancelledRef.current) {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
          sendVoice(blob)
        } else {
          setActivityState('idle')
        }
      }

      isCancelledRef.current = false
      recorder.start(100)
      setMicActive(true)
      setActivityState('listening')
    } catch (e) {
      console.error('Mic error:', e)
      setActivityState('idle')
    }
  }, [setMicActive, setActivityState])

  const stopRecording = useCallback(() => {
    if (!mediaRecorderRef.current) return
    mediaRecorderRef.current.stop()
    mediaRecorderRef.current = null
    setMicActive(false)
  }, [setMicActive])

  const cancelRecording = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    isCancelledRef.current = true
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current = null
    }
    setMicActive(false)
  }, [setMicActive])

  /* ── Send to backend → add transcript + response to chat ──── */
  const sendVoice = async (audioBlob: Blob) => {
    setActivityState('thinking')
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 180000)
    try {
      const { chatSessionId, persona } = useJarvisStore.getState()
      const formData = new FormData()
      formData.append('audio', audioBlob, 'recording.webm')
      formData.append('session_id', chatSessionId)
      formData.append('persona', persona?.name || 'profesional')

      const res = await fetch(`${API}/voice`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      })
      clearTimeout(timeout)
      if (res.ok) {
        const data = await res.json()

        transcriptRef.current = data.transcript || ''
        responseRef.current = data.response_text || ''

        // Si el transcript está vacío (ej. filtro de alucinaciones de Whisper), ignoramos silenciosamente
        if (!transcriptRef.current) {
          setActivityState('idle')
          return
        }

        setLastUserText(transcriptRef.current)
        setLastAssistantText(responseRef.current)

        appendChatMessage({ id: makeId(), role: 'user', content: transcriptRef.current })
        if (responseRef.current) {
          appendChatMessage({ id: makeId(), role: 'assistant', content: responseRef.current })
        }

        if (data.audio_base64) {
          setActivityState('speaking')
          playAudio(data.audio_base64)
        } else {
          // No audio from backend (e.g. Orpheus TTS not available):
          // fall back to Web Speech API in the browser.
          if (responseRef.current && useJarvisStore.getState().voiceEnabled) {
            const success = ttsSpeak(responseRef.current)
            if (!success) setActivityState('idle')
          } else {
            setActivityState('idle')
          }
        }
      } else {
        const errText = await res.text().catch(() => '')
        console.error('Voice API error:', res.status, errText)
        setActivityState('idle')
      }
    } catch (e: any) {
      clearTimeout(timeout)
      if (e?.name !== 'AbortError') {
        console.error('Voice error:', e)
      }
      setActivityState('idle')
    }
  }

  const playAudio = useCallback((base64: string, onEnded?: () => void) => {
    if (audioElRef.current) {
      audioElRef.current.onended = null
      audioElRef.current.onerror = null
      audioElRef.current.pause()
      audioElRef.current.src = ''
      audioElRef.current.load()
    }
    try {
      const src = `data:audio/mp3;base64,${base64}`
      const audio = new Audio(src)
      audioElRef.current = audio
      audio.onended = () => {
        setActivityState('idle')
        audioElRef.current = null
        onEnded?.()
      }
      audio.onerror = () => { setActivityState('idle'); audioElRef.current = null }
      audio.play().catch(() => { setActivityState('idle'); audioElRef.current = null })
    } catch (e) {
      console.error(e)
      setActivityState('idle')
    }
  }, [setActivityState])

  const handleMicClick = () => {
    if (activityState === 'speaking' || activityState === 'thinking') {
      cancelEverything()
      return
    }
    if (!micActive) {
      startRecording()
    } else {
      stopRecording()
    }
  }

  const toggleTTS = () => {
    const next = !voiceEnabled
    setVoiceEnabled(next)
    if (!next) {
      window.speechSynthesis?.cancel()
      if (audioElRef.current) {
        audioElRef.current.onended = null
        audioElRef.current.onerror = null
        audioElRef.current.pause()
        audioElRef.current.src = ''
        audioElRef.current.load()
        audioElRef.current = null
        setActivityState('idle')
      }
    }
  }

  const showControls = currentScreen === 'home'
    || activityState === 'listening'
    || activityState === 'speaking'
    || activityState === 'thinking'

  if (!showControls) return null

  const isActive = activityState !== 'idle'

  return (
    <div className="fixed bottom-24 left-0 right-0 z-45 flex flex-col items-center justify-center pointer-events-none gap-4">
      <div className="pointer-events-auto flex flex-col items-center gap-4">
        <AnimatePresence>
          {isActive && (
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.8 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.8 }}
              transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
              className="relative"
            >
              <canvas
                ref={canvasRef}
                className="rounded-2xl"
                style={{
                  background: 'linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.15) 100%)',
                  filter: 'blur(0.5px)',
                }}
              />
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <motion.p
                  key={activityState}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-[10px] uppercase tracking-[0.3em] font-medium"
                  style={{
                    color: activityState === 'listening' ? 'rgba(0,255,150,0.7)'
                      : activityState === 'thinking' ? 'rgba(255,170,0,0.7)'
                      : 'rgba(100,200,255,0.7)',
                    textShadow: `0 0 20px ${activityState === 'listening' ? 'rgba(0,255,150,0.3)' : activityState === 'thinking' ? 'rgba(255,170,0,0.3)' : 'rgba(100,200,255,0.3)'}`,
                  }}
                >
                  {activityState === 'listening' ? 'Escuchando... (toca para detener)'
                    : activityState === 'thinking' ? 'Procesando... (toca para cancelar)'
                    : 'Jarvis hablando... (toca para interrumpir)'}
                </motion.p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="relative flex items-center justify-center gap-6">
          {isActive && (
            <>
              <motion.div
                className="absolute inset-0 rounded-full"
                animate={{ scale: [1, 1.4, 1], opacity: [0.3, 0, 0.3] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                style={{
                  background: activityState === 'listening'
                    ? 'radial-gradient(circle, rgba(0,255,150,0.3) 0%, transparent 70%)'
                    : activityState === 'thinking'
                      ? 'radial-gradient(circle, rgba(255,170,0,0.3) 0%, transparent 70%)'
                      : 'radial-gradient(circle, rgba(100,200,255,0.3) 0%, transparent 70%)',
                }}
              />
              <motion.div
                className="absolute inset-0 rounded-full"
                animate={{ scale: [1, 1.6, 1], opacity: [0.2, 0, 0.2] }}
                transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
                style={{
                  background: activityState === 'listening'
                    ? 'radial-gradient(circle, rgba(0,255,150,0.2) 0%, transparent 70%)'
                    : activityState === 'thinking'
                      ? 'radial-gradient(circle, rgba(255,170,0,0.2) 0%, transparent 70%)'
                      : 'radial-gradient(circle, rgba(100,200,255,0.2) 0%, transparent 70%)',
                }}
              />
            </>
          )}

          {micActive && (
            <motion.button
              initial={{ opacity: 0, scale: 0.5, x: -20 }}
              animate={{ opacity: 1, scale: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.5, x: -20 }}
              onClick={cancelRecording}
              className="absolute -left-16 w-12 h-12 rounded-full flex items-center justify-center transition-all bg-red-500/10 hover:bg-red-500/30 border border-red-500/30 text-red-400"
              title="Cancelar (borrar grabación)"
            >
              <X className="w-5 h-5" />
            </motion.button>
          )}

          <button
            onClick={handleMicClick}
            onMouseEnter={() => setHoveredBtn('mic')}
            onMouseLeave={() => setHoveredBtn(null)}
            className="relative z-10 w-20 h-20 rounded-full flex items-center justify-center transition-all duration-500 cursor-pointer"
            style={{
              background: micActive
                ? 'radial-gradient(circle, rgba(0,255,150,0.18) 0%, rgba(0,255,150,0.06) 100%)'
                : activityState === 'speaking'
                  ? 'radial-gradient(circle, rgba(100,200,255,0.18) 0%, rgba(100,200,255,0.06) 100%)'
                  : activityState === 'thinking'
                    ? 'radial-gradient(circle, rgba(255,170,0,0.15) 0%, rgba(255,170,0,0.04) 100%)'
                    : 'radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.03) 100%)',
              border: `1.5px solid ${micActive ? 'rgba(0,255,150,0.35)' : activityState === 'speaking' ? 'rgba(100,200,255,0.35)' : activityState === 'thinking' ? 'rgba(255,170,0,0.3)' : 'rgba(255,255,255,0.12)'}`,
              boxShadow: micActive
                ? '0 0 50px rgba(0,255,150,0.25), inset 0 1px 0 rgba(255,255,255,0.15)'
                : activityState === 'speaking'
                  ? '0 0 50px rgba(100,200,255,0.25), inset 0 1px 0 rgba(255,255,255,0.15)'
                  : activityState === 'thinking'
                    ? '0 0 50px rgba(255,170,0,0.2), inset 0 1px 0 rgba(255,255,255,0.1)'
                    : '0 0 30px rgba(255,255,255,0.06), inset 0 1px 0 rgba(255,255,255,0.06)',
            }}
          >
            <motion.div
              animate={micActive ? { scale: [1, 1.1, 1] } : activityState === 'thinking' ? { rotate: [0, 10, -10, 0] } : { scale: hoveredBtn === 'mic' ? 1.08 : 1 }}
              transition={{ duration: activityState === 'thinking' ? 1.5 : 0.4, repeat: activityState === 'thinking' ? Infinity : undefined, ease: 'easeOut' }}
            >
              {micActive ? (
                <Square className="w-8 h-8" style={{ color: '#ff4444', filter: 'drop-shadow(0 0 10px rgba(255,68,68,0.5))' }} />
              ) : activityState === 'speaking' ? (
                <Square className="w-8 h-8" style={{ color: '#00d4ff', filter: 'drop-shadow(0 0 10px rgba(0,212,255,0.5))' }} />
              ) : activityState === 'thinking' ? (
                <div className="w-8 h-8 border-2 border-amber-400/30 border-t-amber-400 rounded-full animate-spin" />
              ) : (
                <Mic className="w-8 h-8" style={{ color: 'rgba(255,255,255,0.7)', filter: 'drop-shadow(0 0 8px rgba(0,212,255,0.3))' }} />
              )}
            </motion.div>
          </button>
        </div>

        <button
          onClick={toggleTTS}
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] tracking-wider uppercase font-medium transition-all cursor-pointer"
          style={{
            background: voiceEnabled ? 'rgba(0,200,255,0.12)' : 'rgba(255,255,255,0.04)',
            border: `1px solid ${voiceEnabled ? 'rgba(0,200,255,0.25)' : 'rgba(255,255,255,0.08)'}`,
            color: voiceEnabled ? 'rgba(0,200,255,0.8)' : 'rgba(255,255,255,0.3)',
          }}
          title={voiceEnabled ? 'Desactivar voz de JARVIS' : 'Activar voz de JARVIS'}
        >
          {voiceEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
          <span>{voiceEnabled ? 'Voz ON' : 'Voz OFF'}</span>
        </button>
      </div>
    </div>
  )
}
