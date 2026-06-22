'use client';

import React, { useEffect, useRef } from 'react';
import { useJarvisStore } from '@/store/jarvisStore';
import { PERSONALITY_THEMES } from '@/constants/colors';

export default function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const activePersonality = useJarvisStore((state) => state.persona?.name) || 'profesional';
  const activityState = useJarvisStore((state) => state.activityState);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = canvas.width = window.innerWidth;
    let h = canvas.height = window.innerHeight;

    const handleResize = () => {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    const theme = PERSONALITY_THEMES[activePersonality] || PERSONALITY_THEMES.profesional;
    let particles: any[] = [];
    let animationFrameId: number;
    let time = 0;

    // Initialize particles based on type
    const initParticles = () => {
      particles = [];
      const count = 100;
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 2,
          vy: (Math.random() - 0.5) * 2,
          size: Math.random() * 2 + 1,
          angle: Math.random() * Math.PI * 2,
          speed: Math.random() * 0.5 + 0.2
        });
      }
    };
    initParticles();

    // Hex to RGB for opacity control
    const hexToRgb = (hex: string) => {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
      return result ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : '255, 255, 255';
    };
    const rgbColor = hexToRgb(theme.hex);

    const draw = () => {
      // Speed multiplier based on voice activity
      let speedMultiplier = 1;
      if (activityState === 'listening') speedMultiplier = 0.2;
      else if (activityState === 'thinking') speedMultiplier = 3.0;
      else if (activityState === 'speaking') speedMultiplier = 1.5;

      const baseSpeed = theme.particleSpeed * speedMultiplier;

      ctx.clearRect(0, 0, w, h);
      time += 0.01 * baseSpeed;

      ctx.fillStyle = `rgba(${rgbColor}, 0.5)`;
      ctx.strokeStyle = `rgba(${rgbColor}, 0.15)`;

      if (theme.particleType === 'grid') {
        const spacing = 40;
        const offset = (time * 20) % spacing;
        ctx.beginPath();
        for (let x = offset; x < w; x += spacing) {
          ctx.moveTo(x, 0);
          ctx.lineTo(x, h);
        }
        for (let y = offset; y < h; y += spacing) {
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
        }
        ctx.stroke();
      } else if (theme.particleType === 'matrix') {
        particles.forEach(p => {
          p.y += p.speed * 5 * baseSpeed;
          if (p.y > h) {
            p.y = 0;
            p.x = Math.random() * w;
          }
          ctx.fillRect(p.x, p.y, 2, 15);
        });
      } else if (theme.particleType === 'waves') {
        ctx.beginPath();
        for (let i = 0; i < 5; i++) {
          for (let x = 0; x < w; x += 10) {
            const y = h / 2 + Math.sin(x * 0.01 + time + i) * 100;
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
      } else if (theme.particleType === 'pulses') {
        const centerX = w / 2;
        const centerY = h / 2;
        for (let i = 0; i < 4; i++) {
          const radius = ((time * 50) + i * 100) % 400;
          ctx.beginPath();
          ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
          ctx.stroke();
        }
      } else {
        // Chaos / Vectors
        particles.forEach(p => {
          p.x += p.vx * baseSpeed;
          p.y += p.vy * baseSpeed;
          if (p.x < 0 || p.x > w) p.vx *= -1;
          if (p.y < 0 || p.y > h) p.vy *= -1;

          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fill();
        });

        if (theme.particleType === 'vectors') {
          ctx.beginPath();
          for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
              const dx = particles[i].x - particles[j].x;
              const dy = particles[i].y - particles[j].y;
              const dist = dx * dx + dy * dy;
              if (dist < 10000) {
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
              }
            }
          }
          ctx.stroke();
        }
      }

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [activePersonality, activityState]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 z-0 pointer-events-none"
      style={{ mixBlendMode: 'screen', opacity: 0.6 }}
    />
  );
}
