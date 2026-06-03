'use client';

import React from 'react';
import { Mic } from 'lucide-react';
import { useJarvisStore } from '@/store/jarvisStore';

/* ── MicButton ─────────────────────────────────────────────────────────
   Floating mic button on home → navigates to VoiceModePanel.
   ───────────────────────────────────────────────────────────────────── */

export default function MicButton() {
  const { setScreen } = useJarvisStore();

  const handleClick = () => {
    setScreen('voice');
  };

  return (
    <button
      onClick={handleClick}
      className="relative flex items-center justify-center w-[72px] h-[72px] rounded-full transition-transform duration-200 touch-target"
      style={{
        background: 'linear-gradient(135deg, #0099cc, #00d4ff)',
        boxShadow: '0 0 30px rgba(0, 212, 255, 0.4), 0 0 60px rgba(0, 212, 255, 0.2)',
      }}
      aria-label="Open voice mode"
    >
      <Mic className="w-7 h-7 text-white" strokeWidth={2} />
    </button>
  );
}
