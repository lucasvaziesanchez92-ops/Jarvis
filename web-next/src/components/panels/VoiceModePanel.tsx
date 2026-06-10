'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, Square, Volume2, AlertCircle, Loader2, Pause, Play } from 'lucide-react';
import { useJarvisStore } from '@/store/jarvisStore';
import { useJarvisChat } from '@/hooks/useJarvisChat';
import {
  speak as ttsSpeak,
  stop as ttsStop,
  pause as ttsPause,
  resume as ttsResume,
  isSpeaking as ttsIsSpeaking,
  isPausedNow as ttsIsPaused,
  onTTSEvent,
  isSupported as ttsIsSupported,
} from '@/lib/tts';

/* ── VoiceModePanel v10 — Voz + Chat integrados, robusto ───────────
   - Web Speech API STT para grabar tu voz (Chrome/Edge)
   - Web Speech API TTS para responder (módulo lib/tts)
   - Pausa/Reanuda la voz con un botón
   - Envía al agente via WebSocket
   - Muestra transcripción en vivo
   - NO depende de flags globales — usa el store de mensajes
   ──────────────────────────────────────────────────────────────────── */

export default function VoiceModePanel() {
  const { setActivityState } = useJarvisStore();
  const { sendMessage: wsSend, isConnected, messages } = useJarvisChat();

  const [status, setStatus] = useState<'idle' | 'recording' | 'thinking' | 'speaking' | 'paused' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [transcript, setTranscript] = useState('');
  const [recordingTime, setRecordingTime] = useState(0);
  const [hasPermission, setHasPermission] = useState(true);

  const recognitionRef = useRef<any>(null);
  const timerRef = useRef<any>(null);
  const spokenIdsRef = useRef<Set<string>>(new Set());

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopTimer();
      try { recognitionRef.current?.abort?.(); } catch {}
      ttsStop();
    };
  }, []);

  // Subscribe to TTS events to update status
  useEffect(() => {
    const off = onTTSEvent((e) => {
      if (e.type === 'start') {
        setStatus('speaking');
        setActivityState('speaking');
      } else if (e.type === 'end') {
        setStatus('idle');
        setActivityState('idle');
      } else if (e.type === 'pause') {
        setStatus('paused');
      } else if (e.type === 'resume') {
        setStatus('speaking');
      } else if (e.type === 'error') {
        // Don't fail loudly — TTS just didn't work, but text is on screen
        setStatus('idle');
        setActivityState('idle');
      }
    });
    return () => off();
  }, [setActivityState]);

  const stopTimer = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }, []);

  const startTimer = useCallback(() => {
    setRecordingTime(0);
    timerRef.current = setInterval(() => setRecordingTime((p) => p + 1), 1000);
  }, []);

  // Auto-speak new assistant messages
  useEffect(() => {
    if (messages.length === 0) return;
    const last = messages[messages.length - 1];
    if (last.role !== 'assistant' || last.isStreaming) return;
    if (spokenIdsRef.current.has(last.id)) return;
    if (!ttsIsSupported()) return;

    spokenIdsRef.current.add(last.id);
    ttsSpeak(last.content);
  }, [messages]);

  const startListening = useCallback(async () => {
    setErrorMsg('');

    // Permission
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      setHasPermission(true);
    } catch {
      setHasPermission(false);
      return;
    }

    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      setErrorMsg('Tu navegador no soporta Speech Recognition. Usa Chrome o Edge.');
      setStatus('error');
      return;
    }

    // If TTS is currently speaking, stop it (user is about to talk)
    ttsStop();

    const rec = new SR();
    rec.lang = 'es-ES';
    rec.continuous = true;
    rec.interimResults = true;
    recognitionRef.current = rec;

    let finalTranscript = '';
    setTranscript('');
    setStatus('recording');
    setActivityState('listening');
    startTimer();

    rec.onresult = (event: any) => {
      let final = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) final += event.results[i][0].transcript;
      }
      if (final) {
        finalTranscript += final;
        setTranscript(finalTranscript);
      }
    };

    rec.onerror = (event: any) => {
      if (event.error === 'no-speech' || event.error === 'aborted') return;
      setErrorMsg(`Error de microfono: ${event.error}`);
      setStatus('error');
      stopTimer();
    };

    rec.onend = () => {
      // If user didn't manually stop, auto-restart
      if (status === 'recording' && recognitionRef.current === rec) {
        try { rec.start(); } catch { /* */ }
      }
    };

    rec.start();
  }, [setActivityState, startTimer, stopTimer, status]);

  const stopListening = useCallback(() => {
    stopTimer();
    const rec = recognitionRef.current;
    recognitionRef.current = null;
    if (rec) {
      try { rec.onend = null; rec.stop(); } catch {}
    }

    const text = transcript.trim();
    if (!text) {
      setStatus('idle');
      setActivityState('idle');
      return;
    }

    if (!isConnected) {
      setErrorMsg('Chat offline. Conectate a Google primero.');
      setStatus('error');
      return;
    }

    // Send to agent
    setStatus('thinking');
    setActivityState('thinking');
    setTranscript('');
    wsSend(text);
  }, [stopTimer, transcript, isConnected, wsSend, setActivityState]);

  // Pause/resume TTS
  const toggleTTS = useCallback(() => {
    if (ttsIsPaused()) {
      ttsResume();
    } else if (ttsIsSpeaking()) {
      ttsPause();
    } else {
      // Nothing playing — no-op
    }
  }, []);

  const formatTime = (s: number) =>
    `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;

  if (!hasPermission) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-4 px-4 text-center">
        <AlertCircle className="w-12 h-12 text-red-400/40" />
        <p className="text-[13px] text-white/40">
          Necesito permiso para usar el microfono.
          <br />
          Hace click en el candado arriba a la izquierda y permiti el acceso.
        </p>
        <button
          onClick={() => { setHasPermission(true); startListening(); }}
          className="mt-2 px-4 py-2 rounded-xl bg-cyan-500/20 border border-cyan-400/30 text-cyan-300 text-[12px] hover:bg-cyan-500/30"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full items-center justify-center gap-5 px-4">
      {/* Main button */}
      <div className="relative">
        <button
          onClick={status === 'recording' ? stopListening : startListening}
          disabled={status === 'thinking'}
          className={`relative w-[92px] h-[92px] rounded-full flex items-center justify-center transition-all duration-300 ${
            status === 'thinking'
              ? 'bg-gradient-to-br from-cyan-500 to-blue-600 opacity-60 cursor-not-allowed'
              : status === 'recording'
                ? 'bg-gradient-to-br from-red-500 to-red-600 shadow-[0_0_30px_rgba(255,68,68,0.5)] animate-pulse'
                : 'bg-gradient-to-br from-cyan-500 to-blue-600 shadow-[0_0_30px_rgba(0,212,255,0.4)] hover:scale-105'
          }`}
        >
          {status === 'recording' && (
            <span className="absolute inset-0 rounded-full border-2 border-white/20 animate-recording-ring" />
          )}
          {status === 'thinking' ? (
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          ) : status === 'speaking' || status === 'paused' ? (
            <Volume2 className="w-8 h-8 text-white animate-pulse" />
          ) : status === 'recording' ? (
            <Square className="w-7 h-7 text-white fill-white" />
          ) : (
            <Mic className="w-8 h-8 text-white" />
          )}
        </button>

        {/* Pause/Resume TTS button (small, bottom-right) */}
        {(status === 'speaking' || status === 'paused') && (
          <button
            onClick={toggleTTS}
            className="absolute -bottom-2 -right-2 w-9 h-9 rounded-full bg-white/10 border border-white/20 flex items-center justify-center hover:bg-white/20"
            title={status === 'paused' ? 'Reanudar voz' : 'Pausar voz'}
          >
            {status === 'paused' ? (
              <Play className="w-4 h-4 text-white fill-white" />
            ) : (
              <Pause className="w-4 h-4 text-white fill-white" />
            )}
          </button>
        )}
      </div>

      {/* Timer */}
      {status === 'recording' && (
        <p className="text-2xl font-mono font-semibold text-red-400 tracking-wider">
          {formatTime(recordingTime)}
        </p>
      )}

      {/* Status text */}
      <p className="text-[11px] text-cyan-400/50 tracking-[0.2em] uppercase text-center">
        {status === 'idle' && (isConnected ? 'Toca el microfono para hablar con JARVIS' : 'Chat offline')}
        {status === 'recording' && 'Escuchando... toca para detener'}
        {status === 'thinking' && 'JARVIS esta pensando...'}
        {status === 'speaking' && 'JARVIS responde en voz alta...'}
        {status === 'paused' && 'Voz pausada — toca play para continuar'}
        {status === 'error' && 'Error'}
      </p>

      {/* Connection status */}
      {!isConnected && (
        <span className="text-[10px] px-2 py-1 rounded-full bg-red-400/10 text-red-400/70 border border-red-400/20">
          Chat offline — conectando...
        </span>
      )}

      {/* TTS availability hint */}
      {!ttsIsSupported() && (
        <p className="text-[10px] text-yellow-400/60 text-center max-w-xs">
          Tu navegador no soporta Web Speech API. Usa Chrome o Edge para escuchar las respuestas.
        </p>
      )}

      {/* Error */}
      {errorMsg && (
        <div className="w-full max-w-sm glass-strong rounded-xl p-3">
          <p className="text-[11px] text-red-400/80 text-center">{errorMsg}</p>
        </div>
      )}

      {/* Live transcript */}
      {transcript && (
        <div className="w-full glass-strong rounded-xl p-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-400/50 mb-1">Escuche</p>
          <p className="text-[14px] text-white/80">{transcript}</p>
        </div>
      )}
    </div>
  );
}
