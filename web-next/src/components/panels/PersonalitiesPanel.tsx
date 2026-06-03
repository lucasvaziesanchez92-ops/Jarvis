'use client';

import React, { useState, useEffect } from 'react';
import { Sparkles, Check, Briefcase, Heart, Wrench, Building2, Palette, LifeBuoy } from 'lucide-react';

/* ── PersonalitiesPanel v2 ───────────────────────────────────────────
   6 personalities from RFP + backward compatibility.
   Shows persona grid with descriptions, tools, and tone info.
   ──────────────────────────────────────────────────────────────────── */

const API = '/api';

interface Persona {
  name: string;
  label: string;
  description: string;
  icon: string;
  tone?: string;
}

const ICON_MAP: Record<string, React.ElementType> = {
  '💼': Briefcase,
  '🤗': Heart,
  '⚙️': Wrench,
  '🏢': Building2,
  '🎨': Palette,
  '🛟': LifeBuoy,
};

const FALLBACK_PERSONAS: Persona[] = [
  { name: 'profesional', label: 'PROFESIONAL', description: 'Clara, formal, eficiente. Tareas de trabajo.', icon: '💼', tone: 'formal' },
  { name: 'amigable', label: 'AMIGABLE', description: 'Cercana, casual, empática.', icon: '🤗', tone: 'casual' },
  { name: 'tecnica', label: 'TÉCNICA', description: 'Precisa, detallada. Ingeniería y configuración.', icon: '⚙️', tone: 'technical' },
  { name: 'ejecutiva', label: 'EJECUTIVA', description: 'Breve, estratégica. Decisiones y resultados.', icon: '🏢', tone: 'executive' },
  { name: 'creativa', label: 'CREATIVA', description: 'Flexible, ideas. Contenido y marketing.', icon: '🎨', tone: 'creative' },
  { name: 'soporte', label: 'SOPORTE', description: 'Paciente, ordenada. Problemas paso a paso.', icon: '🛟', tone: 'patient' },
];

export default function PersonalitiesPanel() {
  const [personas, setPersonas] = useState<Persona[]>(FALLBACK_PERSONAS);
  const [active, setActive] = useState<string>('profesional');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/personas`)
      .then(r => r.json())
      .then((data) => {
        if (!Array.isArray(data)) {
          throw new Error('Invalid response format');
        }
        if (data.length > 0) {
          setPersonas(data);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const activePersona = personas.find(p => p.name === active) || personas[0];

  return (
    <div className="flex flex-col h-full overflow-y-auto scrollbar-hide px-4 py-4 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-[9px] tracking-[0.2em] uppercase text-white/30">Neural Personas</span>
        <Sparkles className="w-4 h-4 text-cyan-400/30" />
      </div>

      {/* Persona grid — 2 columns, 3 rows for 6 personas */}
      <div className="grid grid-cols-2 gap-3">
        {personas.map((p) => {
          const isActive = active === p.name;
          const Icon = ICON_MAP[p.icon] || Briefcase;
          return (
            <button
              key={p.name}
              onClick={() => setActive(p.name)}
              className={`relative p-4 rounded-xl text-left transition-all ${
                isActive
                  ? 'glass-strong border border-cyan-400/30 bg-cyan-400/[0.06]'
                  : 'glass-base hover:bg-white/[0.06]'
              }`}
            >
              {isActive && <Check className="absolute top-2 right-2 w-3 h-3 text-cyan-400" />}
              
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">{p.icon}</span>
                <span className={`text-[13px] font-semibold ${isActive ? 'text-cyan-300' : 'text-white/70'}`}>
                  {p.label}
                </span>
              </div>

              <p className="text-[10px] text-white/40 leading-relaxed">
                {p.description}
              </p>

              {p.tone && (
                <div className="mt-2 flex items-center gap-1">
                  <span className="text-[8px] px-2 py-0.5 rounded-full bg-white/[0.04] text-white/25">
                    {p.tone}
                  </span>
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Active persona details */}
      <div className="glass-base rounded-xl p-4 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{activePersona.icon}</span>
          <div>
            <h4 className="text-[12px] font-semibold text-white/70">{activePersona.label}</h4>
            {activePersona.tone && (
              <span className="text-[10px] text-cyan-400/40">Tono: {activePersona.tone}</span>
            )}
          </div>
        </div>

        <p className="text-[11px] text-white/40 leading-relaxed">
          {activePersona.description}
        </p>

        {/* Activation info */}
        <div className="p-3 rounded-lg bg-cyan-400/[0.04] border border-cyan-400/[0.08]">
          <p className="text-[10px] text-cyan-300/60">
            Seleccioná esta personalidad para que el agente adapte su tono,
            vocabulario y comportamiento según el contexto.
          </p>
        </div>
      </div>

      {loading && (
        <p className="text-[10px] text-white/20 text-center">Cargando personalidades...</p>
      )}
    </div>
  );
}
