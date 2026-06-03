'use client';

import { useRef, useEffect } from 'react';
import { useJarvisStore } from '@/store/jarvisStore';

/* ═══════════════════════════════════════════════════════════
   BRAIN VISUAL — Canvas 2D, based on Tripo3D reference
   
   Luminescent brain, teal/cyan surface, pink/magenta inner
   glow, smooth gyri, translucent. Pure 2D Canvas — no
   Three.js, no WebGL. 100% reliable.
   ═══════════════════════════════════════════════════════════ */

const STATE_COLORS: Record<string, { surface: string; inner: string; glow: string }> = {
  idle:      { surface: '#00b8d4', inner: '#ff0080', glow: 'rgba(0,200,220,0.6)' },
  listening: { surface: '#00e5a0', inner: '#cc00aa', glow: 'rgba(0,230,160,0.7)' },
  thinking:  { surface: '#cc8800', inner: '#ff0066', glow: 'rgba(200,140,0,0.7)' },
  speaking:  { surface: '#00d4ff', inner: '#ff44aa', glow: 'rgba(0,220,255,0.8)' },
  error:     { surface: '#ff4466', inner: '#cc0022', glow: 'rgba(255,70,100,0.7)' },
  sleep:     { surface: '#4455aa', inner: '#223366', glow: 'rgba(60,80,180,0.3)' },
};

// Brain silhouette path (simplified anatomical shape)
function drawBrainOutline(ctx: CanvasRenderingContext2D, cx: number, cy: number, scale: number) {
  const s = scale * 0.6;
  ctx.beginPath();

  // Left hemisphere
  ctx.moveTo(cx, cy - s * 1.4);
  ctx.bezierCurveTo(cx - s * 1.1, cy - s * 1.3, cx - s * 1.5, cy - s * 0.6, cx - s * 1.35, cy + s * 0.1);
  ctx.bezierCurveTo(cx - s * 1.5, cy + s * 0.4, cx - s * 1.2, cy + s * 0.7, cx - s * 0.6, cy + s * 0.9);
  ctx.bezierCurveTo(cx - s * 0.2, cy + s * 1.1, cx - s * 0.1, cy + s * 0.3, cx, cy + s * 0.15);

  // Right hemisphere
  ctx.bezierCurveTo(cx + s * 0.1, cy + s * 0.3, cx + s * 0.2, cy + s * 1.1, cx + s * 0.6, cy + s * 0.9);
  ctx.bezierCurveTo(cx + s * 1.2, cy + s * 0.7, cx + s * 1.5, cy + s * 0.4, cx + s * 1.35, cy + s * 0.1);
  ctx.bezierCurveTo(cx + s * 1.5, cy - s * 0.6, cx + s * 1.1, cy - s * 1.3, cx, cy - s * 1.4);

  // Cerebellum bottom
  ctx.bezierCurveTo(cx - s * 0.4, cy + s * 0.6, cx + s * 0.4, cy + s * 0.6, cx + s * 0.35, cy + s * 0.85);
  ctx.bezierCurveTo(cx + s * 0.08, cy + s * 1.05, cx - s * 0.08, cy + s * 1.05, cx - s * 0.35, cy + s * 0.85);
  ctx.bezierCurveTo(cx - s * 0.4, cy + s * 0.6, cx + s * 0.4, cy + s * 0.6, cx, cy + s * 0.15);

  ctx.closePath();
}

// Gyri/sulci lines
function drawSulci(ctx: CanvasRenderingContext2D, cx: number, cy: number, scale: number, t: number) {
  const s = scale * 0.55;
  ctx.strokeStyle = `rgba(200,200,255,${0.12 + Math.sin(t * 0.7) * 0.04})`;
  ctx.lineWidth = 0.8;

  const curves = [
    // Left hemisphere sulci
    { x1: cx - s * 0.2, y1: cy - s * 0.8, x2: cx - s * 0.7, y2: cy - s * 0.4 },
    { x1: cx - s * 0.1, y1: cy - s * 0.2, x2: cx - s * 0.8, y2: cy + s * 0.15 },
    { x1: cx - s * 0.3, y1: cy + s * 0.4, x2: cx - s * 0.5, y2: cy + s * 0.6 },
    // Right hemisphere sulci
    { x1: cx + s * 0.2, y1: cy - s * 0.8, x2: cx + s * 0.7, y2: cy - s * 0.4 },
    { x1: cx + s * 0.1, y1: cy - s * 0.2, x2: cx + s * 0.8, y2: cy + s * 0.15 },
    { x1: cx + s * 0.3, y1: cy + s * 0.4, x2: cx + s * 0.5, y2: cy + s * 0.6 },
  ];

  for (const c of curves) {
    ctx.beginPath();
    ctx.moveTo(c.x1, c.y1);
    ctx.bezierCurveTo(
      (c.x1 + c.x2) / 2 + Math.sin(t + c.x1) * s * 0.1,
      c.y1 + s * 0.08,
      (c.x1 + c.x2) / 2 - Math.sin(t + c.x2) * s * 0.1,
      c.y2 - s * 0.08,
      c.x2, c.y2
    );
    ctx.stroke();
  }
}

// Particle system around the brain
interface Particle {
  x: number; y: number; vx: number; vy: number;
  size: number; alpha: number; life: number; maxLife: number;
}

function spawnParticles(
  particles: Particle[], cx: number, cy: number, s: number, count: number, color: string
) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const dist = s * (0.9 + Math.random() * 0.5);
    const px = cx + Math.cos(angle) * dist;
    const py = cy + Math.sin(angle) * dist * 0.8;
    particles.push({
      x: px, y: py,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4 - 0.2,
      size: 0.8 + Math.random() * 2,
      alpha: 0.4 + Math.random() * 0.6,
      life: 0,
      maxLife: 100 + Math.random() * 200,
    });
  }
}

export default function BrainVisual({ width = 400, height = 360 }: { width?: number; height?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { activityState } = useJarvisStore();
  const particlesRef = useRef<Particle[]>([]);
  const frameRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio, 2);
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    const cx = width / 2;
    const cy = height / 2 + 10;
    const scale = Math.min(width, height);

    let animId: number;

    function render() {
      frameRef.current++;
      const t = frameRef.current * 0.016;
      const colors = STATE_COLORS[activityState] || STATE_COLORS.idle;

      ctx.clearRect(0, 0, width, height);

      // Ambient glow
      const grad = ctx.createRadialGradient(cx, cy, scale * 0.1, cx, cy, scale * 0.9);
      grad.addColorStop(0, colors.glow);
      grad.addColorStop(0.5, 'transparent');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, width, height);

      // Inner glow behind brain
      drawBrainOutline(ctx, cx, cy, scale);
      ctx.save();
      ctx.clip();
      const innerGrad = ctx.createRadialGradient(cx, cy + scale * 0.1, scale * 0.05, cx, cy, scale * 0.7);
      innerGrad.addColorStop(0, colors.inner);
      innerGrad.addColorStop(0.6, colors.inner.replace('ff', '44'));
      innerGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = innerGrad;
      ctx.fill();
      ctx.restore();

      // Main brain surface — translucent teal/cyan
      drawBrainOutline(ctx, cx, cy, scale);
      const surfaceGrad = ctx.createLinearGradient(cx - scale * 0.5, cy - scale * 0.4, cx + scale * 0.5, cy + scale * 0.4);
      surfaceGrad.addColorStop(0, colors.surface);
      surfaceGrad.addColorStop(0.5, colors.surface.replace(')', ',0.6)').replace('rgb', 'rgba'));
      surfaceGrad.addColorStop(1, colors.inner);
      ctx.fillStyle = surfaceGrad;
      ctx.globalAlpha = 0.55 + Math.sin(t * 0.5) * 0.08;
      ctx.fill();

      // Surface outline
      drawBrainOutline(ctx, cx, cy, scale);
      ctx.strokeStyle = colors.surface;
      ctx.globalAlpha = 0.5;
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.globalAlpha = 1;

      // Sulci
      drawSulci(ctx, cx, cy, scale, t);

      // Spawn particles
      if (particlesRef.current.length < 80) {
        spawnParticles(particlesRef.current, cx, cy, scale * 0.6, 3, colors.glow);
      }

      // Update & draw particles
      for (let i = particlesRef.current.length - 1; i >= 0; i--) {
        const p = particlesRef.current[i];
        p.life++;
        p.x += p.vx;
        p.y += p.vy;
        p.vx += (Math.random() - 0.5) * 0.02;
        p.vy += (Math.random() - 0.5) * 0.02;
        const progress = p.life / p.maxLife;
        const alpha = p.alpha * (1 - progress) * (0.7 + 0.3 * Math.sin(t * 3 + p.x));

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * (1 - progress * 0.5), 0, Math.PI * 2);
        ctx.fillStyle = colors.glow.replace('0.6', alpha.toFixed(2));
        ctx.fill();

        if (p.life >= p.maxLife || alpha < 0.02) {
          particlesRef.current.splice(i, 1);
        }
      }

      // Breathing pulse ring
      const ringRadius = scale * 0.42 + Math.sin(t * 0.6) * 4;
      ctx.beginPath();
      ctx.arc(cx, cy - scale * 0.05, ringRadius, 0, Math.PI * 2);
      ctx.strokeStyle = colors.glow.replace('0.6', '0.12');
      ctx.lineWidth = 3;
      ctx.stroke();

      animId = requestAnimationFrame(render);
    }

    render();
    return () => cancelAnimationFrame(animId);
  }, [width, height, activityState]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none select-none"
      style={{ opacity: 0.9 }}
    />
  );
}
