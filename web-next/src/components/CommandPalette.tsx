'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useJarvisStore } from '@/store/jarvisStore';
import {
  Search,
  MessageSquare,
  CheckCircle2,
  FileText,
  Mic,
  Clock,
  Mail,
  Settings,
  Sparkles,
  X,
  Command,
} from 'lucide-react';

/* ── CommandPalette ────────────────────────────────────────────────────────
   Cmd+K modal for quick navigation and actions.
   ────────────────────────────────────────────────────────────────────────── */

const commands = [
  { id: 'chat', label: 'Chat', description: 'Open neural chat interface', icon: MessageSquare, mode: 'chat' as const },
  { id: 'tasks', label: 'Tasks', description: 'View and manage tasks', icon: CheckCircle2, mode: 'tasks' as const },
  { id: 'notes', label: 'Notes', description: 'Browse your notes', icon: FileText, mode: 'notes' as const },
  { id: 'voice', label: 'Voice', description: 'Voice command mode', icon: Mic, mode: 'voice' as const },
  { id: 'timer', label: 'Timer', description: 'Set a countdown timer', icon: Clock, mode: 'timer' as const },
  { id: 'email', label: 'Email', description: 'Check your emails', icon: Mail, mode: 'email' as const },
  { id: 'personas', label: 'Personas', description: 'Switch AI personality', icon: Sparkles, mode: 'personalities' as const },
  { id: 'settings', label: 'Settings', description: 'App configuration', icon: Settings, mode: 'settings' as const },
];

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const { setPanelMode } = useJarvisStore();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const filteredCommands = commands.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(query.toLowerCase()) ||
      cmd.description.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (mode: 'chat' | 'tasks' | 'notes' | 'voice' | 'timer' | 'email' | 'settings' | 'personalities') => {
    setPanelMode(mode);
    setIsOpen(false);
    setQuery('');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => setIsOpen(false)}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 glass-strong rounded-3xl overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-white/[0.08]">
          <Search className="w-5 h-5 text-cyan-400/60" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search commands..."
            className="flex-1 bg-transparent text-white/90 text-[15px] outline-none placeholder:text-white/30"
          />
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-4 h-4 text-white/40" />
          </button>
        </div>

        {/* Commands list */}
        <div className="max-h-80 overflow-y-auto py-2">
          {filteredCommands.length === 0 ? (
            <div className="px-4 py-8 text-center text-white/30 text-sm">
              No commands found
            </div>
          ) : (
            filteredCommands.map((cmd) => (
              <button
                key={cmd.id}
                onClick={() => handleSelect(cmd.mode)}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/[0.05] transition-colors group"
              >
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center">
                  <cmd.icon className="w-5 h-5 text-cyan-400" />
                </div>
                <div className="flex-1 text-left">
                  <div className="text-white/90 text-[14px] font-medium">{cmd.label}</div>
                  <div className="text-white/40 text-[12px]">{cmd.description}</div>
                </div>
                <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                  <Command className="w-4 h-4 text-white/20" />
                </div>
              </button>
            ))
          )}
        </div>

        {/* Footer hint */}
        <div className="px-4 py-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-white/25">
          <span>Press Enter to select</span>
          <span>Press Esc to close</span>
        </div>
      </div>
    </div>
  );
}
