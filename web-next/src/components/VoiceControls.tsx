'use client'

import { useRef, useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Square, Volume2, VolumeX, X, Eye, EyeOff } from 'lucide-react'
import { useJarvisStore } from '@/store/jarvisStore'
import { speak as ttsSpeak, stop as ttsStop, onTTSEvent } from '@/lib/tts'
import { AudioQueuePlayer } from '@/utils/AudioQueuePlayer'
import { ScreenCapturer } from '@/utils/ScreenCapturer'
import { useMicVAD, utils } from '@ricky0123/vad-react'

const API = '/api'
const WS_URL = typeof window !== 'undefined' ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/api/voice/stream` : ''

if (typeof window !== 'undefined') {
  // @ts-ignore
  window.ort = window.ort || {};
  // @ts-ignore
  window.ort.env = window.ort.env || {};
  // @ts-ignore
  window.ort.env.wasm = window.ort.env.wasm || {};
  // @ts-ignore
  window.ort.env.wasm.wasmPaths = {
    "ort-wasm-simd-threaded.wasm": "/ort-wasm-simd-threaded.wasm",
    "ort-wasm-simd-threaded.mjs": "/ort-wasm-simd-threaded.mjs",
    "ort-wasm-simd.wasm": "/ort-wasm-simd-threaded.wasm",
    "ort-wasm.wasm": "/ort-wasm-simd-threaded.wasm",
  }
}

export default function VoiceControls() {
  const {
    activityState, setActivityState, setMicActive, micActive,
    visualizerAmplitude, voiceEnabled, setVoiceEnabled, currentScreen,
    appendChatMessage, setLastUserText, setLastAssistantText, setScreen,
  } = useJarvisStore()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)
  const [hoveredBtn, setHoveredBtn] = useState<string | null>(null)
  const [visionActive, setVisionActive] = useState<boolean>(false)

  const isCancelledRef = useRef<boolean>(false)
  const ignoreSpeechRef = useRef<boolean>(false)
  const wsRef = useRef<WebSocket | null>(null)
  const audioQueueRef = useRef<AudioQueuePlayer | null>(null)
  const screenCapturerRef = useRef<ScreenCapturer | null>(null)

  const vad = useMicVAD({
    startOnLoad: false,
    baseAssetPath: "/",
    onnxWASMBasePath: "/",
    positiveSpeechThreshold: 0.4, // Umbral bajo para que no corte si baja un poco la voz
    negativeSpeechThreshold: 0.2, // Umbral bajo para mantenerlo activo
    redemptionMs: 2000, // 2 segundos enteros de pausa tolerada antes de enviar el audio
    onSpeechStart: () => {
      const currentState = useJarvisStore.getState().activityState;
      if (currentState === 'thinking') {
        console.log("⏳ [VAD] Ignorando ruido porque JARVIS está pensando...");
        ignoreSpeechRef.current = true;
        return;
      }
      
      ignoreSpeechRef.current = false;
      isCancelledRef.current = false;
      console.log("🎙️ [VAD] Detección de habla iniciada.");
      
      // 1. BARGE-IN ORGÁNICO: Si JARVIS está hablando, lo callamos al instante
      if (currentState === 'speaking') {
        console.log("🛑 [VAD] Interrupción detectada. Enviando señal de aborto...");
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'abort' }))
        }
        if (audioQueueRef.current) {
          audioQueueRef.current.clearQueue()
        }
        window.speechSynthesis?.cancel()
      }
      setActivityState('listening')
    },
    onSpeechEnd: (audioFloat32Array) => {
      if (ignoreSpeechRef.current) {
        console.log("⏳ [VAD] Fin de habla ignorado (inició mientras JARVIS pensaba).");
        ignoreSpeechRef.current = false;
        return;
      }

      if (isCancelledRef.current) {
        console.log("❌ [VAD] Audio descartado por cancelación.");
        isCancelledRef.current = false;
        return;
      }
      console.log("✅ [VAD] Fin del habla detectado. Procesando audio...");
      const wavBuffer = utils.encodeWAV(audioFloat32Array)
      const audioBlob = new Blob([wavBuffer], { type: 'audio/wav' })
      sendVoice(audioBlob)
    },
    onVADMisfire: () => {
      console.log("💨 [VAD] Ruido ambiental o respiración corta descartada.");
      setActivityState('idle')
    }
  })

  // Sincronizar el estado de animación del Canvas con la energía detectada
  useEffect(() => {
    const currentState = useJarvisStore.getState().activityState;
    if (vad.userSpeaking && currentState !== 'listening' && currentState !== 'thinking') {
      setActivityState('listening')
    } else if (!vad.userSpeaking && currentState === 'listening') {
      // Solo transicionar a thinking si el VAD fue quien nos puso en listening
      setActivityState('thinking')
    }
    setMicActive(!vad.loading && vad.listening)
  }, [vad.userSpeaking, vad.loading, vad.listening, setActivityState, setMicActive])

  useEffect(() => {
    if (typeof window !== 'undefined' && !audioQueueRef.current) {
      audioQueueRef.current = new AudioQueuePlayer()
    }
    if (typeof window !== 'undefined' && !screenCapturerRef.current) {
      screenCapturerRef.current = new ScreenCapturer()
    }
    return () => {
      screenCapturerRef.current?.detenerCaptura()
    }
  }, [])

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
  const cancelEverything = useCallback((e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    isCancelledRef.current = true
    
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'abort' }))
      }
      wsRef.current.close()
      wsRef.current = null
    }

    if (audioQueueRef.current) {
      audioQueueRef.current.clearQueue()
    }

    window.speechSynthesis?.cancel()

    setActivityState('idle')
  }, [setActivityState])

  useEffect(() => {
    return () => {
      if (audioElRef.current) {
        audioElRef.current.pause()
        audioElRef.current.src = ''
        audioElRef.current.load()
      }
    }
  }, [])



  /* ── Send to backend via WebSocket (Real-Time Audio Streaming) ──── */
  const sendVoice = async (audioBlob: Blob) => {
    setActivityState('thinking')
    const { chatSessionId, persona, showThinkingBubble, hideThinkingBubble, setLastUserText, setLastAssistantText } = useJarvisStore.getState()
    
    try {
      if (wsRef.current) {
        wsRef.current.close()
      }
      
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        // Convert Blob to Base64
        const reader = new FileReader()
        reader.readAsDataURL(audioBlob)
        reader.onloadend = () => {
          const base64data = (reader.result as string).split(',')[1]
          ws.send(JSON.stringify({
            type: 'audio_input',
            payload: base64data,
            session_id: chatSessionId,
            persona: persona?.name || 'profesional'
          }))
        }
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'state') {
            if (data.status === 'thinking') {
              showThinkingBubble('Procesando...')
            } else if (data.status === 'idle') {
              // Si ya terminó de mandar audio, podemos esperar a que la cola termine o forzar idle
              // Pero lo manejamos en el onended del AudioQueuePlayer idealmente
            }
          }

          if (data.type === 'thought') {
            showThinkingBubble(data.payload)
          }

          if (data.type === 'audio_chunk') {
            hideThinkingBubble()
            setActivityState('speaking')
            if (audioQueueRef.current) {
              audioQueueRef.current.queueAudioChunk(data.payload)
            }
          }

          if (data.type === 'done') {
            hideThinkingBubble()
            
            // Append to chat panel
            if (data.transcript) {
              setLastUserText(data.transcript)
              appendChatMessage({ id: makeId(), role: 'user', content: data.transcript })
            }
            if (data.response_text) {
              setLastAssistantText(data.response_text)
              appendChatMessage({ id: makeId(), role: 'assistant', content: data.response_text })
            }

            // Si el backend terminó y NO hay audio reproduciéndose (ej. gTTS falló o el LLM respondió muy poco)
            // debemos liberar la interfaz, de lo contrario se quedará pensando para siempre.
            if (!audioQueueRef.current || !audioQueueRef.current.isPlaying) {
              setActivityState('idle')
              hideThinkingBubble()
            }

            // If the voice was disabled, just set idle immediately
            if (!useJarvisStore.getState().voiceEnabled) {
              setActivityState('idle')
              ws.close()
            }
          }
          
          if (data.type === 'error') {
            console.error('WS Voice Error:', data.payload)
            hideThinkingBubble()
            setActivityState('idle')
            ws.close()
          }

        } catch (err) {
          console.error("Error parsing WS message:", err)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket Error:', error)
        hideThinkingBubble()
        setActivityState('idle')
      }

      ws.onclose = () => {
        wsRef.current = null
      }

    } catch (error) {
      console.error('Error enviando audio por WebSocket:', error)
      hideThinkingBubble()
      setActivityState('idle')
    }
  }



  const handleMicClick = () => {
    // Reanudar el AudioContext del navegador con el gesto del usuario
    if (audioQueueRef.current) {
      audioQueueRef.current.resumeContext()
    }
    
    if (activityState === 'speaking' || activityState === 'thinking') {
      cancelEverything()
      vad.pause()
      return
    }
    vad.toggle()
  }

  const toggleTTS = () => {
    const next = !voiceEnabled
    setVoiceEnabled(next)
    if (!next) {
      window.speechSynthesis?.cancel()
      if (audioQueueRef.current) {
        audioQueueRef.current.clearQueue()
        setActivityState('idle')
      }
      if (wsRef.current) {
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'abort' }))
        }
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }

  const toggleVision = async () => {
    if (visionActive) {
      screenCapturerRef.current?.detenerCaptura()
      setVisionActive(false)
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'clear_screen' }))
      }
    } else {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        // Debemos asegurar que el ws esté abierto para transmitir
        // Podemos iniciar la captura de todas formas y el ws transmitirá cuando esté ready
        const ws = new WebSocket(WS_URL)
        wsRef.current = ws
        ws.onclose = () => { wsRef.current = null }
      }
      await screenCapturerRef.current?.iniciarCaptura(wsRef.current!, 3000, () => setVisionActive(false))
      setVisionActive(true)
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
              onClick={(e) => { cancelEverything(e); vad.pause(); }}
              className="absolute -left-16 w-12 h-12 flex items-center justify-center transition-all bg-red-500/10 hover:bg-red-500/30 border border-red-500/30 text-red-400 rounded-full"
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

        <span className="text-[10px] font-mono tracking-widest font-medium" style={{ color: vad.loading ? '#888' : vad.userSpeaking ? '#00ff96' : '#64c8ff' }}>
          {vad.loading ? "CARGANDO VAD..." : vad.userSpeaking ? "TE ESCUCHO" : vad.listening ? "CONECTADO" : "PAUSADO"}
        </span>

        <div className="flex gap-4">
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
          
          <button
            onClick={toggleVision}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] tracking-wider uppercase font-medium transition-all cursor-pointer"
            style={{
              background: visionActive ? 'rgba(167,139,250,0.12)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${visionActive ? 'rgba(167,139,250,0.35)' : 'rgba(255,255,255,0.08)'}`,
              color: visionActive ? 'rgba(167,139,250,0.9)' : 'rgba(255,255,255,0.3)',
              boxShadow: visionActive ? '0 0 10px rgba(167,139,250,0.2)' : 'none'
            }}
            title={visionActive ? 'Desactivar Módulo de Visión' : 'Activar Módulo de Visión'}
          >
            {visionActive ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span>{visionActive ? 'Visión ON' : 'Visión OFF'}</span>
          </button>
        </div>
      </div>
    </div>
  )
}
