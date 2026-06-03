'use client';

import React, { useState, useEffect } from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';

/* ── TimerModePanel ───────────────────────────────────────────────────
   Pomodoro timer with focus/short/long presets.
   ──────────────────────────────────────────────────────────────────── */

const PRESETS = { focus: 25 * 60, short: 5 * 60, long: 15 * 60 };

export default function TimerModePanel() {
  const [seconds, setSeconds] = useState(PRESETS.focus);
  const [isRunning, setIsRunning] = useState(false);
  const [mode, setMode] = useState<keyof typeof PRESETS>('focus');

  useEffect(() => {
    if (!isRunning) return;
    const id = setInterval(() => {
      setSeconds(s => {
        if (s <= 0) { setIsRunning(false); return 0; }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [isRunning]);

  const setPreset = (m: keyof typeof PRESETS) => {
    setMode(m);
    setSeconds(PRESETS[m]);
    setIsRunning(false);
  };

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  };

  const progress = 1 - seconds / PRESETS[mode];

  const modeColor = {
    focus: '#00d4ff',
    short: '#00ff88',
    long: '#ffaa00',
  };

  return (
    <div className="flex flex-col items-center justify-center h-full gap-5 py-6">
      {/* Mode tabs */}
      <div className="flex gap-2">
        {(Object.keys(PRESETS) as Array<keyof typeof PRESETS>).map((m) => (
          <button
            key={m}
            onClick={() => setPreset(m)}
            className={`px-3 py-1.5 rounded-lg text-[10px] font-medium uppercase tracking-wider transition-all ${
              mode === m
                ? 'glass-strong border-cyan-400/20 text-cyan-300'
                : 'glass-base text-white/30 hover:text-white/50'
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Timer circle */}
      <div className="relative w-40 h-40">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="3" />
          <circle
            cx="50" cy="50" r="42" fill="none"
            stroke={modeColor[mode]}
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 42}`}
            strokeDashoffset={`${2 * Math.PI * 42 * (1 - progress)}`}
            style={{ transition: 'stroke-dashoffset 1s linear' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-mono font-bold tracking-wider" style={{ color: modeColor[mode], textShadow: `0 0 20px ${modeColor[mode]}40` }}>
            {fmt(seconds)}
          </span>
          <span className="text-[9px] text-white/30 tracking-widest uppercase mt-1">
            {isRunning ? 'Running' : 'Paused'}
          </span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex gap-3">
        <button
          onClick={() => setIsRunning(!isRunning)}
          className="px-6 py-2.5 rounded-xl text-[13px] font-medium btn-cyan"
        >
          {isRunning ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
        </button>
        <button
          onClick={() => { setSeconds(PRESETS[mode]); setIsRunning(false); }}
          className="px-4 py-2.5 rounded-xl text-[13px] text-white/40 border border-white/[0.08] hover:text-white/60 transition-all"
        >
          <RotateCcw className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
