'use client';

/**
 * JARVIS TTS — robust Spanish speech synthesis.
 *
 * Strategy:
 *  1. Web Speech API (browser-native, FREE, Spanish voices preinstalled).
 *  2. Optional: Groq TTS for English/cloud fallback (when user enables it).
 *
 * Why Web Speech API first:
 *  - 100% free, zero auth, zero network, zero latency.
 *  - Native Spanish voices: Paulina (es-MX), Helena/Maria (es-ES), Jorge (es-MX).
 *  - Works offline.
 *  - Can be paused/resumed via SpeechSynthesis.pause() / .resume().
 *
 * Robustness:
 *  - Wait for voiceschanged (Chrome loads voices async).
 *  - Auto-prepend one silent utterance to unlock autoplay (Chrome policy).
 *  - Detect iOS Safari quirk (utterances on iOS are cut after ~10s).
 *  - Emit events: onstart / onend / onerror / onpause / onresume so the UI
 *    can show "JARVIS hablando..." / "JARVIS pausado".
 *  - Chunk long texts (Web Speech API cuts at ~15s on some browsers).
 *  - Fallback to no-TTS silently if browser doesn't support it.
 */

export type TTSEvent =
  | { type: 'start'; text: string }
  | { type: 'end' }
  | { type: 'error'; message: string }
  | { type: 'pause' }
  | { type: 'resume' }
  | { type: 'voices'; voices: SpeechSynthesisVoice[] };

type Listener = (e: TTSEvent) => void;

const listeners = new Set<Listener>();
let currentUtter: SpeechSynthesisUtterance | null = null;
let isPaused = false;
let voicesReady = false;
let voicePref: { name?: string; lang?: string } = { lang: 'es-ES' };
let primedForAutoplay = false;
let chunkQueue: string[] = [];
let chunkIndex = 0;

function emit(e: TTSEvent) {
  listeners.forEach((l) => {
    try {
      l(e);
    } catch {
      /* ignore */
    }
  });
}

export function onTTSEvent(l: Listener): () => void {
  listeners.add(l);
  // If voices are already loaded, fire them immediately
  if (voicesReady) {
    l({ type: 'voices', voices: getSpanishVoices() });
  }
  return () => listeners.delete(l);
}

function getSpanishVoices(): SpeechSynthesisVoice[] {
  if (typeof window === 'undefined' || !window.speechSynthesis) return [];
  return window.speechSynthesis.getVoices().filter((v) => v.lang?.toLowerCase().startsWith('es'));
}

function pickBestVoice(): SpeechSynthesisVoice | null {
  const voces = getSpanishVoices();
  if (voces.length === 0) return null;

  // Priority list: highest quality first
  const preferred = [
    // Mexican Spanish (natural, warm)
    { name: 'Paulina', lang: 'es-MX' },
    { name: 'Microsoft Sabina - Spanish (Mexico)', lang: 'es-MX' },
    { name: 'Google español de México', lang: 'es-MX' },
    // Castilian Spanish
    { name: 'Microsoft Helena - Spanish (Spain)', lang: 'es-ES' },
    { name: 'Google español de España', lang: 'es-ES' },
    { name: 'Monica', lang: 'es-ES' },
    { name: 'Maria', lang: 'es-ES' },
    { name: 'Esperanza', lang: 'es-ES' },
    // Any other Spanish
    { name: 'Jorge', lang: 'es-MX' },
    { name: 'Diego', lang: 'es-ES' },
  ];

  for (const p of preferred) {
    const v = voces.find((v) => v.name === p.name);
    if (v) return v;
  }

  // Fallback: local es-MX, then local es-ES, then any es
  return (
    voces.find((v) => v.lang === 'es-MX' && v.localService) ||
    voces.find((v) => v.lang === 'es-ES' && v.localService) ||
    voces.find((v) => v.lang === 'es') ||
    voces[0]
  );
}

function initVoices() {
  if (typeof window === 'undefined' || !window.speechSynthesis) return;
  const update = () => {
    const voces = getSpanishVoices();
    voicesReady = true;
    const best = pickBestVoice();
    if (best) voicePref = { name: best.name, lang: best.lang };
    emit({ type: 'voices', voices: voces });
  };
  // Chrome loads voices async
  if (window.speechSynthesis.getVoices().length > 0) {
    update();
  } else {
    window.speechSynthesis.addEventListener('voiceschanged', update);
  }
}

/**
 * Strip markdown, code blocks, URLs, emojis, and other characters
 * that sound terrible when read by TTS. Keep the natural language.
 */
export function cleanForSpeech(text: string): string {
  if (!text) return '';
  return text
    // Code blocks
    .replace(/```[\s\S]*?```/g, ' bloque de código ')
    .replace(/`([^`]+)`/g, '$1')
    // Headers
    .replace(/^#{1,6}\s+/gm, '')
    // Bold/italic
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    // Bullets
    .replace(/^[-*+]\s+/gm, '')
    .replace(/^\d+\.\s+/gm, '')
    // Links: keep label, drop URL
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // HTML
    .replace(/<[^>]+>/g, ' ')
    // Emojis
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '')
    // Markdown table separators
    .replace(/^\|?[-\s|:]+\|?$/gm, '')
    // Multiple newlines -> pause
    .replace(/\n{2,}/g, '. ')
    .replace(/\n/g, ', ')
    // Multiple spaces
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Split text into chunks of ~150 chars at sentence boundaries.
 * Web Speech API tends to cut off at ~15s on some browsers.
 */
function chunkText(text: string, maxLen = 150): string[] {
  if (text.length <= maxLen) return [text];
  const sentences = text.split(/(?<=[.!?])\s+/);
  const chunks: string[] = [];
  let current = '';
  for (const s of sentences) {
    if ((current + ' ' + s).trim().length > maxLen && current) {
      chunks.push(current.trim());
      current = s;
    } else {
      current = current ? current + ' ' + s : s;
    }
  }
  if (current.trim()) chunks.push(current.trim());
  return chunks;
}

/**
 * Prime the Web Speech API to bypass Chrome's autoplay policy.
 * Chrome blocks the first speechSynthesis call until the user
 * has interacted with the page. We send a silent utterance
 * the first time the user clicks anywhere.
 */
function primeAutoplay() {
  if (primedForAutoplay) return;
  if (typeof window === 'undefined' || !window.speechSynthesis) return;
  const u = new SpeechSynthesisUtterance(' ');
  u.volume = 0;
  u.rate = 1;
  u.lang = 'es-ES';
  try {
    window.speechSynthesis.speak(u);
    primedForAutoplay = true;
  } catch {
    /* ignore */
  }
}

// Prime on first user interaction (any click/tap/key)
if (typeof window !== 'undefined') {
  const prime = () => {
    primeAutoplay();
    window.removeEventListener('click', prime);
    window.removeEventListener('keydown', prime);
    window.removeEventListener('touchstart', prime);
  };
  window.addEventListener('click', prime, { once: true });
  window.addEventListener('keydown', prime, { once: true });
  window.addEventListener('touchstart', prime, { once: true });
}

// Initialize voices on load
if (typeof window !== 'undefined') {
  initVoices();
}

/**
 * Speak text. Auto-cancels anything currently speaking.
 * Returns false if TTS is not available (browser doesn't support it).
 */
export function speak(text: string): boolean {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    emit({ type: 'error', message: 'Web Speech API no disponible' });
    return false;
  }

  const cleaned = cleanForSpeech(text);
  if (!cleaned) {
    emit({ type: 'end' });
    return true;
  }

  // Cancel any in-progress speech
  window.speechSynthesis.cancel();
  isPaused = false;
  currentUtter = null;
  chunkQueue = chunkText(cleaned);
  chunkIndex = 0;

  const speakNext = () => {
    if (chunkIndex >= chunkQueue.length) {
      currentUtter = null;
      emit({ type: 'end' });
      return;
    }
    const chunk = chunkQueue[chunkIndex++];
    const utter = new SpeechSynthesisUtterance(chunk);
    utter.lang = voicePref.lang || 'es-ES';
    utter.rate = 1.0;
    utter.pitch = 1.0;
    utter.volume = 1.0;
    const best = pickBestVoice();
    if (best) utter.voice = best;

    utter.onstart = () => {
      isPaused = false;
      currentUtter = utter;
      emit({ type: 'start', text: chunk });
    };
    utter.onend = () => {
      if (isPaused) return; // user paused, don't continue
      currentUtter = null;
      // Continue with next chunk
      if (chunkIndex < chunkQueue.length) {
        // Tiny delay so the browser can process
        setTimeout(speakNext, 80);
      } else {
        emit({ type: 'end' });
      }
    };
    utter.onerror = (e) => {
      // 'interrupted' / 'canceled' are normal (user cancelled or new speech)
      if (e.error === 'interrupted' || e.error === 'canceled') {
        return;
      }
      emit({ type: 'error', message: `TTS error: ${e.error || 'unknown'}` });
      // Try next chunk anyway
      if (chunkIndex < chunkQueue.length) {
        setTimeout(speakNext, 100);
      } else {
        emit({ type: 'end' });
      }
    };
    utter.onpause = () => emit({ type: 'pause' });
    utter.onresume = () => emit({ type: 'resume' });

    try {
      window.speechSynthesis.speak(utter);
    } catch (e) {
      emit({ type: 'error', message: `speak() falló: ${(e as Error).message}` });
      return false;
    }
  };

  speakNext();
  return true;
}

/**
 * Pause the current speech. Calling speak() resumes by cancelling
 * and starting fresh, so use this only to keep state consistent.
 */
export function pause(): void {
  if (typeof window === 'undefined' || !window.speechSynthesis) return;
  if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
    window.speechSynthesis.pause();
    isPaused = true;
    emit({ type: 'pause' });
  }
}

export function resume(): void {
  if (typeof window === 'undefined' || !window.speechSynthesis) return;
  if (window.speechSynthesis.paused) {
    window.speechSynthesis.resume();
    isPaused = false;
    emit({ type: 'resume' });
  }
}

export function stop(): void {
  if (typeof window === 'undefined' || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  isPaused = false;
  currentUtter = null;
  chunkQueue = [];
  chunkIndex = 0;
  emit({ type: 'end' });
}

export function isSpeaking(): boolean {
  if (typeof window === 'undefined' || !window.speechSynthesis) return false;
  return window.speechSynthesis.speaking;
}

export function isPausedNow(): boolean {
  if (typeof window === 'undefined' || !window.speechSynthesis) return false;
  return window.speechSynthesis.paused;
}

export function getVoices(): SpeechSynthesisVoice[] {
  return getSpanishVoices();
}

export function isSupported(): boolean {
  return typeof window !== 'undefined' && !!window.speechSynthesis;
}
