'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, Square, Volume2, AlertCircle, Loader2 } from 'lucide-react';
import { useJarvisStore } from '@/store/jarvisStore';
import { useJarvisChat } from '@/hooks/useJarvisChat';

/* ── VoiceModePanel v9 — Voz conectada al Chat real ───────────────────
   1. Graba tu voz con Web Speech API (Chrome STT)
   2. Manda el texto al agente via WebSocket chat
   3. Escucha nuevas respuestas del asistente y las lee en voz alta
   4. NO depende de flags globales — usa el store de mensajes
   ──────────────────────────────────────────────────────────────────── */

export default function VoiceModePanel() {
  const { setActivityState } = useJarvisStore();
  const { sendMessage: wsSend, isConnected, messages } = useJarvisChat();

  const [status, setStatus] = useState<'idle'|'recording'|'thinking'|'speaking'|'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [transcript, setTranscript] = useState('');
  const [recordingTime, setRecordingTime] = useState(0);
  const [hasPermission, setHasPermission] = useState(true);

  const recognitionRef = useRef<any>(null);
  const timerRef = useRef<any>(null);
  // Ref para trackear qué mensajes ya fueron leidos por voz
  const spokenIdsRef = useRef<Set<string>>(new Set());

  // Cleanup
  useEffect(() => {
    return () => {
      stopTimer();
      recognitionRef.current?.abort?.();
      window.speechSynthesis?.cancel();
    };
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }, []);

  const startTimer = useCallback(() => {
    setRecordingTime(0);
    timerRef.current = setInterval(() => setRecordingTime((p) => p + 1), 1000);
  }, []);

  // Efecto: cuando llega respuesta del asistente, hablarla
  useEffect(() => {
    if (messages.length === 0) return;
    const last = messages[messages.length - 1];
    if (last.role !== 'assistant' || last.isStreaming) return;
    if (spokenIdsRef.current.has(last.id)) return;

    // Marcar como leido y hablar
    spokenIdsRef.current.add(last.id);
    speakText(last.content);
  }, [messages]);

  const speakText = useCallback((text: string) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'es-ES';
    utter.rate = 1.0;
    utter.pitch = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const es = voices.find((v) => v.lang?.startsWith('es'));
    if (es) utter.voice = es;
    utter.onstart = () => { setStatus('speaking'); setActivityState('speaking'); };
    utter.onend = () => { setStatus('idle'); setActivityState('idle'); };
    utter.onerror = () => { setStatus('idle'); setActivityState('idle'); };
    window.speechSynthesis.speak(utter);
  }, [setActivityState]);

  const startListening = useCallback(async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      setHasPermission(true);
    } catch {
      setHasPermission(false);
      return;
    }

    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      setErrorMsg('Tu navegador no soporta Speech API. Usa Chrome o Edge.');
      setStatus('error');
      return;
    }

    const rec = new SR();
    rec.lang = 'es-ES';
    rec.continuous = true;
    rec.interimResults = true;
    recognitionRef.current = rec;

    let finalTranscript = '';
    setTranscript('');
    setErrorMsg('');
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
      if (event.error === 'no-speech') return;
      setErrorMsg(`Error: ${event.error}`);
    };

    rec.onend = () => {
      if (status === 'recording') {
        try { rec.start(); } catch { /* */ }
      }
    };

    rec.start();
  }, [setActivityState, startTimer, status]);

  const stopListening = useCallback(() => {
    stopTimer();
    recognitionRef.current?.stop?.();
    recognitionRef.current = null;

    const text = transcript.trim();
    if (!text) {
      setStatus('idle');
      setActivityState('idle');
      return;
    }

    if (!isConnected) {
      setErrorMsg('Chat offline. El agente no puede responder ahora.');
      setStatus('error');
      return;
    }

    // Enviar al chat real del agente
    setStatus('thinking');
    setActivityState('thinking');
    wsSend(text);
  }, [stopTimer, transcript, isConnected, wsSend, setActivityState]);

  const formatTime = (s: number) =>
    `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;

  if (!hasPermission) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-4 px-4 text-center">
        <AlertCircle className="w-12 h-12 text-red-400/40" />
        <p className="text-[13px] text-white/40">
          Necesito permiso para usar el microfono.
          <br />
          Hace click en el candado arriba a la izquierda y permití el acceso.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full items-center justify-center gap-5 px-4">
      {/* Main button */}
      <button
        onClick={status === 'recording' ? stopListening : startListening}
        disabled={status === 'thinking' || status === 'speaking'}
        className={`relative w-[92px] h-[92px] rounded-full flex items-center justify-center transition-all duration-300 ${
          status === 'thinking' || status === 'speaking'
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
        ) : status === 'speaking' ? (
          <Volume2 className="w-8 h-8 text-white animate-pulse" />
        ) : status === 'recording' ? (
          <Square className="w-7 h-7 text-white fill-white" />
        ) : (
          <Mic className="w-8 h-8 text-white" />
        )}
      </button>

      {/* Timer */}
      {status === 'recording' && (
        <p className="text-2xl font-mono font-semibold text-red-400 tracking-wider">
          {formatTime(recordingTime)}
        </p>
      )}

      {/* Status text */}
      <p className="text-[11px] text-cyan-400/50 tracking-[0.2em] uppercase text-center">
        {status === 'idle' && (isConnected ? 'Toca el microfono para hablar con JARVIS' : 'Chat offline')}
        {status === 'recording' && 'Escuchando... hace click para detener'}
        {status === 'thinking' && 'JARVIS esta pensando...'}
        {status === 'speaking' && 'JARVIS responde en voz alta...'}
        {status === 'error' && 'Error'}
      </p>

      {/* Connection status */}
      {!isConnected && (
        <span className="text-[10px] px-2 py-1 rounded-full bg-red-400/10 text-red-400/70 border border-red-400/20">
          Chat offline — conectando...
        </span>
      )}

      {/* Error */}
      {errorMsg && (
        <div className="w-full max-w-sm glass-strong rounded-xl p-3">
          <p className="text-[11px] text-red-400/80 text-center">{errorMsg}</p>
        </div>
      )}

      {/* Transcript */}
      {transcript && (
        <div className="w-full glass-strong rounded-xl p-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-400/50 mb-1">Escuche</p>
          <p className="text-[14px] text-white/80">{transcript}</p>
        </div>
      )}
    </div>
  );
}
