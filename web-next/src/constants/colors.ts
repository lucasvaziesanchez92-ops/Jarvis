export const PERSONALITY_THEMES: Record<string, {
  hex: string;
  tailwind: string;
  bgGlow: string;
  particleType: 'grid' | 'waves' | 'matrix' | 'vectors' | 'chaos' | 'pulses';
  particleSpeed: number;
}> = {
  profesional: {
    hex: '#ec4899', // Pink
    tailwind: 'text-pink-500',
    bgGlow: 'rgba(236, 72, 153, 0.15)',
    particleType: 'grid',
    particleSpeed: 0.5,
  },
  amigable: {
    hex: '#06b6d4', // Cyan
    tailwind: 'text-cyan-500',
    bgGlow: 'rgba(6, 182, 212, 0.15)',
    particleType: 'waves',
    particleSpeed: 1.2,
  },
  tecnica: {
    hex: '#10b981', // Emerald
    tailwind: 'text-emerald-500',
    bgGlow: 'rgba(16, 185, 129, 0.15)',
    particleType: 'matrix',
    particleSpeed: 2.0,
  },
  ejecutiva: {
    hex: '#f59e0b', // Amber
    tailwind: 'text-amber-500',
    bgGlow: 'rgba(245, 158, 11, 0.15)',
    particleType: 'vectors',
    particleSpeed: 0.8,
  },
  creativa: {
    hex: '#8b5cf6', // Violet
    tailwind: 'text-violet-500',
    bgGlow: 'rgba(139, 92, 246, 0.15)',
    particleType: 'chaos',
    particleSpeed: 2.5,
  },
  soporte: {
    hex: '#f97316', // Orange
    tailwind: 'text-orange-500',
    bgGlow: 'rgba(249, 115, 22, 0.15)',
    particleType: 'pulses',
    particleSpeed: 0.4,
  },
};
