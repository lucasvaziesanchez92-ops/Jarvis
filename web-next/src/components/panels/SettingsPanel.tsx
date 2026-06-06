'use client';

import React, { useState, useEffect } from 'react';
import { Save, RotateCcw, Check, AlertTriangle } from 'lucide-react';
import { API_BASE } from '@/lib/api';
import { useJarvisStore } from '@/store/jarvisStore';


interface AppSettings {
  apiUrl: string;
  llmProvider: string;
  modelName: string;
  theme: 'dark' | 'light';
  autoConnect: boolean;
  enableAnimations: boolean;
  enableTTS: boolean;
  enableSTT: boolean;
  maxContextMessages: number;
}

const DEFAULTS: AppSettings = {
  apiUrl: API_BASE,
  llmProvider: 'ollama',
  modelName: 'minimax-m2.7',
  theme: 'dark',
  autoConnect: true,
  enableAnimations: true,
  enableTTS: true,
  enableSTT: true,
  maxContextMessages: 50,
};

function loadSettings(): AppSettings {
  try {
    const stored = localStorage.getItem('jarvis_settings');
    return stored ? { ...DEFAULTS, ...JSON.parse(stored) } : DEFAULTS;
  } catch { return DEFAULTS; }
}

export default function SettingsPanel() {
  const [settings, setSettings] = useState<AppSettings>(loadSettings);
  const [saved, setSaved] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'ok' | 'error'>('checking');
  const { brainMode, setBrainMode } = useJarvisStore();

  useEffect(() => {
    fetch(`${settings.apiUrl}/api/v1/health`, { method: 'GET', signal: AbortSignal.timeout(3000) })
      .then(r => r.ok ? setBackendStatus('ok') : setBackendStatus('error'))
      .catch(() => setBackendStatus('error'));
  }, [settings.apiUrl]);

  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    const next = { ...settings, [key]: value };
    setSettings(next);
    localStorage.setItem('jarvis_settings', JSON.stringify(next));
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  const reset = () => {
    setSettings(DEFAULTS);
    localStorage.setItem('jarvis_settings', JSON.stringify(DEFAULTS));
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto scrollbar-hide px-4 py-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between"
      >
        <span className="text-[9px] tracking-[0.2em] uppercase text-white/30">System Configuration</span>
        <div className="flex items-center gap-2"
        >
          {saved && (
            <span className="flex items-center gap-1 text-[10px] text-green-400/70"
            >
              <Check className="w-3 h-3" /> Saved
            </span>
          )}
        </div>
      </div>

      {/* Backend Status */}
      <div className="glass-base rounded-xl p-3"
      >
        <div className="flex items-center gap-2 mb-2"
        >
          <span className={`w-2 h-2 rounded-full ${backendStatus === 'ok' ? 'bg-green-400' : backendStatus === 'error' ? 'bg-red-400' : 'bg-amber-400 animate-pulse'}`} 
          />
          <span className="text-[11px] text-white/60"
          >
            Backend: {backendStatus === 'ok' ? 'Connected' : backendStatus === 'error' ? 'Disconnected' : 'Checking...'}
          </span>
        </div>
        {backendStatus === 'error' && (
          <p className="text-[10px] text-red-400/60 flex items-center gap-1"
          >
            <AlertTriangle className="w-3 h-3" /> Check that backend is running on {settings.apiUrl}
          </p>
        )}
      </div>

      {/* API Configuration */}
      <section className="space-y-3"
      >
        <h3 className="text-[10px] tracking-[0.15em] uppercase text-white/30 font-medium"
        >API Configuration</h3>
        
        <div className="space-y-2"
        >
          <label className="text-[11px] text-white/50 block"
          >API Base URL</label>
          <input
            value={settings.apiUrl}
            onChange={e => update('apiUrl', e.target.value)}
            className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-2 text-[13px] text-white/80 outline-none focus:border-cyan-400/30 btn-focus transition-all"
          />
        </div>

        <div className="space-y-2"
        >
          <label className="text-[11px] text-white/50 block"
          >LLM Provider</label>
          <select
            value={settings.llmProvider}
            onChange={e => update('llmProvider', e.target.value)}
            className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-2 text-[13px] text-white/80 outline-none focus:border-cyan-400/30 btn-focus transition-all appearance-none"
          >
            <option value="lm_studio">LM Studio</option>
            <option value="ollama">Ollama</option>
            <option value="bedrock">AWS Bedrock</option>
          </select>
        </div>

        <div className="space-y-2"
        >
          <label className="text-[11px] text-white/50 block"
          >Model Name</label>
          <input
            value={settings.modelName}
            onChange={e => update('modelName', e.target.value)}
            className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-2 text-[13px] text-white/80 outline-none focus:border-cyan-400/30 btn-focus transition-all"
          />
        </div>
      </section>

      {/* Visualizer Mode */}
      <section className="space-y-3">
        <h3 className="text-[10px] tracking-[0.15em] uppercase text-white/30 font-medium">Visualización del Cerebro</h3>
        <div className="grid grid-cols-2 gap-2">
          {['hologram', 'wireframe', 'solid', 'pbr', 'unlit', 'normal', 'toon', 'sketch'].map(mode => (
            <button
              key={mode}
              onClick={() => setBrainMode(mode)}
              className={`px-3 py-2 rounded-xl border text-[10px] font-bold tracking-wider uppercase transition-all active:scale-95 text-center cursor-pointer ${
                brainMode === mode
                  ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_12px_rgba(68,204,221,0.2)]'
                  : 'bg-white/[0.02] border-white/[0.08] text-white/60 hover:text-white hover:border-white/20'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="space-y-3"
      >
        <h3 className="text-[10px] tracking-[0.15em] uppercase text-white/30 font-medium"
        >Features</h3>
        
        {[
          { key: 'autoConnect' as const, label: 'Auto-connect on startup' },
          { key: 'enableAnimations' as const, label: 'UI Animations' },
          { key: 'enableTTS' as const, label: 'Text-to-Speech (TTS)' },
          { key: 'enableSTT' as const, label: 'Speech-to-Text (STT)' },
        ].map(({ key, label }) => (
          <label key={key} className="flex items-center justify-between py-1 cursor-pointer"
          >
            <span className="text-[12px] text-white/60"
            >{label}</span>
            <button
              onClick={() => update(key, !settings[key])}
              className={`w-9 h-5 rounded-full transition-all relative ${settings[key] ? 'bg-cyan-400/30' : 'bg-white/10'}`}
            >
              <span className={`absolute top-[2px] w-4 h-4 rounded-full transition-all ${settings[key] ? 'left-[18px] bg-cyan-400' : 'left-[2px] bg-white/40'}`} 
              />
            </button>
          </label>
        ))}
      </section>

      {/* Danger */}
      <section className="pt-4 border-t border-white/[0.06]"
      >
        <button
          onClick={reset}
          className="flex items-center gap-2 text-[11px] text-red-400/50 hover:text-red-400/80 transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset to defaults
        </button>
      </section>
    </div>
  );
}
