'use client';

import React, { useEffect, useRef } from 'react';
import { useJarvisStore } from '@/store/jarvisStore';

/* ── AudioVisualizer ───────────────────────────────────────────────────
   Bar-based waveform visualizer. 20 bars that animate with amplitude.
   ───────────────────────────────────────────────────────────────────── */

export default function AudioVisualizer() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { activityState, micActive } = useJarvisStore();
  const isActive = activityState === 'speaking' || activityState === 'listening' || micActive;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const barCount = 24;
    const bars: number[] = new Array(barCount).fill(0);

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };

    resize();
    window.addEventListener('resize', resize);

    const animate = () => {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;

      ctx.clearRect(0, 0, w, h);

      const barWidth = (w - (barCount - 1) * 2) / barCount;
      const gap = 2;

      for (let i = 0; i < barCount; i++) {
        let target = 0;

        if (isActive) {
          // Generate organic waveform
          const time = Date.now() / 1000;
          target =
            Math.sin(time * 3 + i * 0.5) * 0.3 +
            Math.sin(time * 5 + i * 0.8) * 0.2 +
            Math.random() * 0.4;
          target = Math.max(0.05, Math.min(0.95, target));
        } else {
          // Gentle idle wave
          const time = Date.now() / 1000;
          target = Math.sin(time * 1.5 + i * 0.3) * 0.08 + 0.1;
        }

        // Smooth interpolation
        bars[i] += (target - bars[i]) * 0.15;

        const barH = bars[i] * h;
        const x = i * (barWidth + gap);
        const y = (h - barH) / 2;

        // Gradient fill
        const gradient = ctx.createLinearGradient(0, y + barH, 0, y);
        if (isActive && activityState === 'listening') {
          gradient.addColorStop(0, 'rgba(0, 255, 136, 0.8)');
          gradient.addColorStop(1, 'rgba(0, 255, 136, 0.2)');
        } else if (isActive) {
          gradient.addColorStop(0, 'rgba(0, 212, 255, 0.8)');
          gradient.addColorStop(1, 'rgba(0, 212, 255, 0.2)');
        } else {
          gradient.addColorStop(0, 'rgba(0, 212, 255, 0.3)');
          gradient.addColorStop(1, 'rgba(0, 212, 255, 0.05)');
        }

        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, barWidth, barH);
      }

      animId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, [isActive, activityState]);

  return (
    <div className="w-full h-14 glass-base rounded-xl overflow-hidden neon-border">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ display: 'block' }}
      />
    </div>
  );
}
