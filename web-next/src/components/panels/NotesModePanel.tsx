'use client';

import React, { useState, useEffect } from 'react';
import { FileText, Trash2, Plus, ChevronLeft, Pencil } from 'lucide-react';
import { NoteCardSkeleton } from '@/components/Skeleton';

interface Note {
  id: string; title: string; content: string; tags: string[]
}

const API = '/api';

export default function NotesModePanel() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);

  const fetchNotes = async () => {
    try {
      const res = await fetch(`${API}/notes`);
      if (!res.ok) throw new Error('Failed to fetch notes');
      const data = await res.json();
      if (!Array.isArray(data)) throw new Error('Invalid response format');
      setNotes(data);
      setError(null);
    } catch (e) {
      setError('Could not connect to backend');
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchNotes(); }, []);

  const addNote = () => {
    if (!newTitle.trim()) return;
    const note = { id: crypto.randomUUID(), title: newTitle, content: newContent || '', tags: ['general'] };
    setNotes(prev => [...prev, note]);
    setNewTitle(''); setNewContent(''); setIsCreating(false);
    fetch(`${API}/notes`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newTitle, content: newContent || '', tags: ['general'] }),
    }).catch(() => {});
  };

  const deleteNote = (id: string) => {
    setNotes(prev => prev.filter(n => n.id !== id));
    if (selectedNote?.id === id) setSelectedNote(null);
    fetch(`${API}/notes/${id}`, { method: 'DELETE' }).catch(() => {});
  };

  if (selectedNote) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.05] shrink-0">
          <button onClick={() => setSelectedNote(null)} className="flex items-center gap-1 text-xs text-cyan-400/60 hover:text-cyan-400 transition-colors">
            <ChevronLeft className="w-3.5 h-3.5" /> Notas
          </button>
          <div className="flex-1" />
          <button onClick={() => deleteNote(selectedNote.id)} className="p-1 text-white/20 hover:text-red-400 transition-colors">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <h2 className="text-base font-bold text-white/90">{selectedNote.title}</h2>
          <div className="flex flex-wrap gap-1.5">
            {selectedNote.tags.map(tag => (
              <span key={tag} className="text-[9px] tracking-wider uppercase px-2 py-0.5 rounded-full border border-cyan-400/10 text-cyan-300/50 bg-[rgba(0,212,255,0.04)]">{tag}</span>
            ))}
          </div>
          <div className="border-t border-white/[0.05] pt-4">
            <div className="text-sm text-white/70 whitespace-pre-wrap leading-[1.8]">{selectedNote.content || '(sin contenido)'}</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.06] shrink-0">
        <span className="text-[9px] tracking-[0.2em] uppercase text-white/30">Neural Notes</span>
        <span className="text-[9px] text-white/15">{notes.length} notas</span>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 scrollbar-hide">
        {loading && <><NoteCardSkeleton /><NoteCardSkeleton /><NoteCardSkeleton /></>}
        {!loading && error && <div className="text-center py-8 text-red-400/60 text-xs">{error}</div>}
        {!loading && !error && notes.length === 0 && (
          <p className="text-xs text-white/20 text-center mt-8">Creá tu primera nota.</p>
        )}

        {notes.map((note) => (
          <div key={note.id} onClick={() => setSelectedNote(note)}
            className="glass-base rounded-xl p-3.5 group transition-all hover:glass-hover cursor-pointer border border-white/[0.04] hover:border-white/[0.08]">
            <div className="flex items-start justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <FileText className="w-3.5 h-3.5 text-cyan-400/50 shrink-0" />
                <h4 className="text-[13px] font-semibold text-cyan-300/90 truncate">{note.title}</h4>
              </div>
              <button onClick={(e) => { e.stopPropagation(); deleteNote(note.id); }}
                className="opacity-0 group-hover:opacity-100 p-1 text-white/15 hover:text-red-400 transition-all shrink-0">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed line-clamp-2 mb-2">{note.content}</p>
            <div className="flex gap-1.5 flex-wrap">
              {note.tags.map(tag => (
                <span key={tag} className="text-[9px] tracking-wider uppercase px-2 py-0.5 rounded-full border border-cyan-400/10 text-cyan-300/50 bg-[rgba(0,212,255,0.04)]">{tag}</span>
              ))}
            </div>
          </div>
        ))}

        {isCreating ? (
          <div className="glass-strong rounded-xl p-3.5 space-y-2.5">
            <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Título..." autoFocus
              className="w-full bg-white/[0.03] border border-white/[0.08] rounded-lg px-3 py-2 text-[13px] text-white/90 outline-none placeholder:text-white/20 focus:border-cyan-400/30 transition-all" />
            <textarea value={newContent} onChange={e => setNewContent(e.target.value)} placeholder="Contenido..." rows={4}
              className="w-full bg-white/[0.03] border border-white/[0.08] rounded-lg px-3 py-2 text-[12px] text-white/80 outline-none placeholder:text-white/15 focus:border-cyan-400/30 resize-none transition-all" />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setIsCreating(false)} className="px-3 py-1.5 rounded-lg text-[11px] text-white/30 hover:text-white/50">Cancelar</button>
              <button onClick={addNote} className="px-3 py-1.5 rounded-lg text-[11px] btn-cyan">Guardar</button>
            </div>
          </div>
        ) : (
          <button onClick={() => setIsCreating(true)}
            className="w-full py-3 rounded-xl border border-dashed border-white/[0.08] text-white/20 hover:text-cyan-300/60 hover:border-cyan-400/20 transition-all text-[12px] tracking-wider flex items-center justify-center gap-1">
            <Plus className="w-4 h-4" /> Nueva nota
          </button>
        )}
      </div>
    </div>
  );
}

