'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square } from 'lucide-react';
import { useJarvisStore } from '@/store/jarvisStore';
import { Button } from '@/components/ui/button';

/* ═══════════════════════════════════════════════════════════
   VOICE BUTTON — Centered beneath JARVIS entity
   
   Large circular mic button with recording state:
   - Idle: Cyan gradient glow ring
   - Recording: Red pulse + expanding rings
   - Processing: Disabled with spinner
   ═══════════════════════════════════════════════════════════ */

const API = '/api';

export default function VoiceButton() {
  const { setActivityState } = useJarvisStore();
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      chunksRef.current = [];
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        streamRef.current = null;
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        await sendVoice(blob);
        if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
        setRecordingTime(0);
      };

      recorder.start(100);
      setIsRecording(true);
      setActivityState('listening');
      timerRef.current = setInterval(() => setRecordingTime(p => p + 1), 1000);
    } catch (e) {
      console.error('Mic error:', e);
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const sendVoice = async (audioBlob: Blob) => {
    setIsProcessing(true);
    setActivityState('thinking');
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('session_id', 'voice-' + Date.now());
      const res = await fetch(`${API}/voice`, { method: 'POST', body: formData });
      if (res.ok) {
        const data = await res.json();
        playAudio(data.audio_base64);
        setActivityState('speaking');
      } else {
        setActivityState('idle');
      }
    } catch (e) {
      console.error('Voice error:', e);
      setActivityState('idle');
    } finally {
      setIsProcessing(false);
    }
  };

  const playAudio = (b64: string) => {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: 'audio/wav' });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => { setActivityState('idle'); URL.revokeObjectURL(url); };
    audio.onerror = () => { setActivityState('idle'); };
    audio.play();
  };

  const formatTime = (s: number) => `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;

  return (
    <div className="flex flex-col items-center gap-3">
      {isRecording && (
        <span className="text-xl font-mono font-semibold text-red-400 tracking-wider">
          {formatTime(recordingTime)}
        </span>
      )}

      {isProcessing && (
        <span className="text-xs text-cyan-400/50 tracking-[0.2em] uppercase animate-pulse">
          Processing...
        </span>
      )}

      <Button
        size="lg"
        variant="ghost"
        disabled={isProcessing}
        onClick={isRecording ? stopRecording : startRecording}
        className={`relative rounded-full w-[72px] h-[72px] p-0 transition-all duration-300 ${
          isProcessing
            ? 'bg-gray-700/50 cursor-not-allowed'
            : isRecording
              ? 'bg-gradient-to-br from-red-500 to-red-700 shadow-[0_0_40px_rgba(255,68,68,0.5)] hover:shadow-[0_0_50px_rgba(255,68,68,0.7)]'
              : 'bg-gradient-to-br from-cyan-500 to-blue-700 shadow-[0_0_30px_rgba(0,212,255,0.4)] hover:shadow-[0_0_40px_rgba(0,212,255,0.6)] hover:scale-110'
        }`}
      >
        {isProcessing ? (
          <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : isRecording ? (
          <Square className="w-7 h-7 text-white fill-white" />
        ) : (
          <Mic className="w-8 h-8 text-white" />
        )}

        {isRecording && (
          <span className="absolute inset-0 rounded-full border-2 border-white/20 animate-recording-ring" />
        )}
      </Button>

      {!isRecording && !isProcessing && (
        <span className="text-[10px] tracking-[0.2em] uppercase text-white/15">
          Toca para hablar
        </span>
      )}
    </div>
  );
}
