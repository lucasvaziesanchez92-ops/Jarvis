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
      if (activityState === 'listening') speedMultiplier = 0.5;
      else if (activityState === 'thinking') speedMultiplier = 5.0;
      else if (activityState === 'speaking') speedMultiplier = 2.5;

      const baseSpeed = theme.particleSpeed * speedMultiplier;

      // Vortex effect with a trailing fade
      ctx.fillStyle = `rgba(4, 4, 8, ${activityState === 'thinking' ? 0.3 : 0.1})`;
      ctx.fillRect(0, 0, w, h);
      
      time += 0.01 * baseSpeed;

      particles.forEach((p) => {
        // Compute distance from center
        const dx = p.x - w / 2;
        const dy = p.y - h / 2;
        const dist = Math.sqrt(dx * dx + dy * dy);
        
        // Swirl angle
        const angle = Math.atan2(dy, dx);
        
        // Vortex force: pulls inward slightly while rotating
        const force = 100 / (dist + 1);
        p.vx += Math.cos(angle + Math.PI / 2) * force * 0.01 * baseSpeed;
        p.vy += Math.sin(angle + Math.PI / 2) * force * 0.01 * baseSpeed;
        
        // Add some noise
        p.vx += (Math.random() - 0.5) * 0.1 * baseSpeed;
        p.vy += (Math.random() - 0.5) * 0.1 * baseSpeed;
        
        // Friction
        p.vx *= 0.98;
        p.vy *= 0.98;

        p.x += p.vx;
        p.y += p.vy;

        // Wrap around if it goes way off screen or gets too close to center
        if (p.x < 0 || p.x > w || p.y < 0 || p.y > h || dist < 20) {
          p.x = Math.random() * w;
          p.y = Math.random() * h;
          p.vx = 0;
          p.vy = 0;
        }

        // Draw particle trail
        ctx.beginPath();
        const intensity = Math.max(0.1, 1 - dist / (w/2));
        ctx.strokeStyle = `rgba(${rgbColor}, ${intensity * 0.8})`;
        ctx.lineWidth = p.size * (activityState === 'thinking' ? 2 : 1);
        ctx.moveTo(p.x - p.vx * 2, p.y - p.vy * 2);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
        
        // Draw particle head
        ctx.fillStyle = `rgba(${rgbColor}, ${intensity})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      });
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
