/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'jarvis-black': '#000308',
        'jarvis-cyan': '#00f2ff',
        'jarvis-cyan-dim': 'rgba(0,242,255,0.45)',
        'jarvis-green': '#00ff88',
        'jarvis-blue': '#0066cc',
        'jarvis-dark': '#030308',
        'jarvis-border': '#1a1a2e',
      },
      fontFamily: {
        sans: ["'Inter'", "'SF Pro'", "'system-ui'", 'sans-serif'],
        mono: ["'SF Mono'", "'Fira Code'", "'JetBrains Mono'", 'monospace'],
      },
      letterSpacing: {
        hero: '10px',
        sub: '4px',
      },
      textShadow: {
        glow: '0 0 30px rgba(0,242,255,0.9)',
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        blink: 'blink 1s step-end infinite',
        'scanline': 'scanline 8s linear infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.6', transform: 'scale(1.5)' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'jarvis-glow': 'radial-gradient(ellipse at 50% 0%, rgba(0,242,255,0.08) 0%, transparent 60%)',
      },
    },
  },
  plugins: [
    function ({ addUtilities }) {
      addUtilities({
        '.glass': {
          background: 'rgba(255,255,255,0.03)',
          backdropFilter: 'blur(24px) saturate(180%)',
          WebkitBackdropFilter: 'blur(24px) saturate(180%)',
          border: '1px solid rgba(255,255,255,0.08)',
        },
        '.glass-strong': {
          background: 'rgba(0, 0, 0, 0.35)',
          backdropFilter: 'blur(28px) saturate(160%)',
          WebkitBackdropFilter: 'blur(28px) saturate(160%)',
          border: '1px solid rgba(0, 242, 255, 0.12)',
        },
        '.neon-border': {
          boxShadow: '0 0 8px rgba(0,242,255,0.15), inset 0 0 4px rgba(0,242,255,0.05)',
          border: '1px solid rgba(0,242,255,0.25)',
        },
        '.neon-border-hover': {
          transition: 'all 0.3s ease',
        },
        '.glow-cyan': {
          boxShadow: '0 0 12px rgba(0,242,255,0.25), 0 0 4px rgba(0,242,255,0.15)',
        },
        '.glow-cyan-strong': {
          boxShadow: '0 0 20px rgba(0,242,255,0.4), 0 0 8px rgba(0,242,255,0.2)',
        },
        '.glow-magenta': {
          boxShadow: '0 0 12px rgba(255,0,255,0.25), 0 0 4px rgba(255,0,255,0.15)',
        },
        '.glow-green': {
          boxShadow: '0 0 12px rgba(0,255,136,0.25), 0 0 4px rgba(0,255,136,0.15)',
        },
        '.text-glow': {
          textShadow: '0 0 8px rgba(0,242,255,0.6), 0 0 20px rgba(0,242,255,0.3)',
        },
        '.text-glow-strong': {
          textShadow: '0 0 10px rgba(0,242,255,0.8), 0 0 30px rgba(0,242,255,0.5), 0 0 60px rgba(0,242,255,0.2)',
        },
        '.gradient-cyan-magenta': {
          background: 'linear-gradient(135deg, #00f2ff 0%, #ff00ff 100%)',
        },
      });
    },
  ],
};
