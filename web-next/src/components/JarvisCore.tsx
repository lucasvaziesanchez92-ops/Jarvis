'use client';

import { useJarvisStore, type ActivityState } from '@/store/jarvisStore';

/* ═══════════════════════════════════════════════════════════
   JARVIS CORE — Entity Animation
   
   The central visual representation of JARVIS. An animated
   orb that breathes, pulses, and changes color based on 
   the AI's current state.
   
   States:
     idle      → Cyan pulsing, breathing rhythm
     listening → Green, expanding concentric rings
     thinking  → Amber, rotating inner particles
     speaking  → White, intense glow + ripple
     error     → Red, rapid flicker
     sleep     → Dim blue, slow fade
   ═══════════════════════════════════════════════════════════ */

const STATE_STYLES: Record<ActivityState, {
  core: string;
  glow: string;
  middle: string;
  outer: string;
  particles: boolean;
  rings: boolean;
}> = {
  idle: {
    core: 'bg-gradient-to-br from-cyan-400 to-blue-600 shadow-[0_0_60px_rgba(0,212,255,0.5)]',
    glow: 'from-cyan-500/20 via-cyan-400/5 to-transparent',
    middle: 'border-cyan-400/30',
    outer: 'border-cyan-400/10',
    particles: false,
    rings: false,
  },
  listening: {
    core: 'bg-gradient-to-br from-green-400 to-emerald-600 shadow-[0_0_70px_rgba(0,255,136,0.6)]',
    glow: 'from-green-500/25 via-green-400/8 to-transparent',
    middle: 'border-green-400/40',
    outer: 'border-green-400/15',
    particles: false,
    rings: true,
  },
  thinking: {
    core: 'bg-gradient-to-br from-amber-400 to-orange-600 shadow-[0_0_60px_rgba(255,170,0,0.5)]',
    glow: 'from-amber-500/20 via-amber-400/5 to-transparent',
    middle: 'border-amber-400/30',
    outer: 'border-amber-400/10',
    particles: true,
    rings: false,
  },
  speaking: {
    core: 'bg-gradient-to-br from-white via-cyan-200 to-white shadow-[0_0_80px_rgba(255,255,255,0.6)]',
    glow: 'from-white/20 via-cyan-300/8 to-transparent',
    middle: 'border-white/40',
    outer: 'border-cyan-300/20',
    particles: false,
    rings: true,
  },
  error: {
    core: 'bg-gradient-to-br from-red-400 to-red-700 shadow-[0_0_60px_rgba(255,68,68,0.6)]',
    glow: 'from-red-500/25 via-red-400/8 to-transparent',
    middle: 'border-red-400/40',
    outer: 'border-red-400/15',
    particles: false,
    rings: false,
  },
  sleep: {
    core: 'bg-gradient-to-br from-blue-800 to-indigo-900 shadow-[0_0_30px_rgba(68,68,255,0.3)]',
    glow: 'from-blue-600/10 via-blue-400/3 to-transparent',
    middle: 'border-blue-500/15',
    outer: 'border-blue-500/5',
    particles: false,
    rings: false,
  },
};

export default function JarvisCore({ size = 180, minimal = false }: { size?: number; minimal?: boolean }) {
  const { activityState } = useJarvisStore();
  const st = STATE_STYLES[activityState];

  const s = minimal ? size * 0.4 : size;

  return (
    <div className="relative flex items-center justify-center" style={{ width: s * 2, height: s * 2 }}>
      {/* Ambient background glow */}
      <div
        className="absolute rounded-full bg-gradient-to-br blur-3xl animate-ambient-pulse"
        style={{
          width: s * 2.5,
          height: s * 2.5,
          background: `radial-gradient(circle, ${st.glow.split(' ')[0].replace('from-','')} 0%, transparent 60%)`,
        }}
      />

      {/* Outer ring */}
      <div
        className={`absolute rounded-full border-2 ${st.outer} animate-pulse-glow`}
        style={{ width: s * 1.4, height: s * 1.4, animationDuration: '3s' }}
      />

      {/* Listening/Speaking concentric rings */}
      {st.rings && (
        <>
          <div
            className="absolute rounded-full border animate-recording-ring"
            style={{
              width: s * 0.9, height: s * 0.9,
              borderColor: activityState === 'speaking' ? 'rgba(255,255,255,0.3)' : 'rgba(0,255,136,0.3)',
            }}
          />
          <div
            className="absolute rounded-full border animate-recording-ring"
            style={{
              width: s * 0.7, height: s * 0.7,
              borderColor: activityState === 'speaking' ? 'rgba(255,255,255,0.2)' : 'rgba(0,255,136,0.2)',
              animationDelay: '0.4s',
            }}
          />
        </>
      )}

      {/* Middle ring */}
      <div
        className={`absolute rounded-full border ${st.middle} animate-float`}
        style={{ width: s * 1.1, height: s * 1.1, animationDuration: '5s' }}
      />

      {/* Core orb */}
      <div
        className={`relative rounded-full ${st.core} transition-all duration-500`}
        style={{ width: s * 0.55, height: s * 0.55 }}
      >
        {/* Inner glow */}
        <div
          className="absolute inset-4 rounded-full bg-white/20 blur-sm"
        />

        {/* Thinking particles */}
        {st.particles && (
          <>
            <div className="absolute w-2 h-2 rounded-full bg-white/60 top-2 left-1/2 -translate-x-1/2 animate-pulse" />
            <div className="absolute w-1.5 h-1.5 rounded-full bg-white/40 bottom-3 right-3 animate-pulse" style={{ animationDelay: '0.3s' }} />
            <div className="absolute w-1.5 h-1.5 rounded-full bg-white/40 bottom-2 left-3 animate-pulse" style={{ animationDelay: '0.6s' }} />
          </>
        )}

        {/* Error flicker */}
        {activityState === 'error' && (
          <div className="absolute inset-0 rounded-full bg-red-400/30 animate-pulse" style={{ animationDuration: '0.5s' }} />
        )}
      </div>
    </div>
  );
}
