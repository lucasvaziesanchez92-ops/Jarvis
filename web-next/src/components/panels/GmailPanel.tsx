'use client';

import React, { useState, useEffect } from 'react';
import { Mail, Search, Loader2, AlertCircle, Clock, ChevronLeft, Send, X, PenLine, RefreshCw, Star, Archive, Inbox } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { API_BASE } from '@/lib/api';

interface EmailItem {
  id: string; thread_id: string; from: string; subject: string; date: string; snippet: string;
}
interface EmailDetail extends EmailItem { to: string; body: string; }

const FILTERS = ['Todos', 'No leídos'] as const;

function SenderAvatar({ from }: { from: string }) {
  const clean = from.replace(/<.*>/, '').trim();
  const initial = (clean || '?')[0].toUpperCase();
  const colors = ['bg-blue-500/20 text-blue-300 border-blue-500/30', 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    'bg-violet-500/20 text-violet-300 border-violet-500/30', 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    'bg-rose-500/20 text-rose-300 border-rose-500/30', 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'];
  const color = colors[initial.charCodeAt(0) % colors.length];
  return (
    <div className={cn('w-9 h-9 rounded-full border flex items-center justify-center shrink-0', color)}>
      <span className="text-[11px] font-bold">{initial}</span>
    </div>
  );
}

export default function GmailPanel() {
  const [emails, setEmails] = useState<EmailItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [connected, setConnected] = useState<boolean | null>(null);
  const [selectedEmail, setSelectedEmail] = useState<EmailDetail | null>(null);
  const [showCompose, setShowCompose] = useState(false);
  const [composeTo, setComposeTo] = useState('');
  const [composeSubject, setComposeSubject] = useState('');
  const [composeBody, setComposeBody] = useState('');
  const [sending, setSending] = useState(false);
  const [activeFilter, setActiveFilter] = useState<string>('Todos');

  useEffect(() => { checkStatus(); }, []);

  async function checkStatus() {
    try {
      const res = await fetch(`${API_BASE}/auth/google/status`);
      const data = await res.json();
      setConnected(data.connected ?? false);
      if (data.connected) fetchEmails();
    } catch { setConnected(false); }
  }

  async function fetchEmails(query: string = '') {
    setLoading(true); setError('');
    try {
      const url = query
        ? `${API_BASE}/api/v1/gmail/search?q=${encodeURIComponent(query)}&max_results=30`
        : `${API_BASE}/api/v1/gmail/list?max_results=30`;
      const res = await fetch(url);
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || 'Error fetching emails'); }
      setEmails(await res.json());
    } catch (e: any) { setError(e.message); if (e.message?.includes('no está conectado')) setConnected(false); }
    finally { setLoading(false); }
  }

  async function fetchEmailDetail(id: string) {
    try {
      const res = await fetch(`${API_BASE}/api/v1/gmail/${id}`);
      if (!res.ok) throw new Error('Error fetching email');
      setSelectedEmail(await res.json());
    } catch (e: any) { setError(e.message); }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!composeTo.trim() || !composeSubject.trim()) return;
    setSending(true); setError('');
    try {
      const res = await fetch(`${API_BASE}/api/v1/gmail/send`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to: composeTo, subject: composeSubject, body: composeBody }),
      });
      if (!res.ok) throw new Error('Error enviando correo');
      setShowCompose(false); setComposeTo(''); setComposeSubject(''); setComposeBody('');
      fetchEmails();
    } catch (e: any) { setError(e.message); }
    finally { setSending(false); }
  }

  function formatEmailDate(dateStr: string) {
    try {
      const d = new Date(dateStr);
      const now = new Date();
      return d.toDateString() === now.toDateString()
        ? d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
        : d.toLocaleDateString('es-AR', { month: 'short', day: 'numeric' });
    } catch { return dateStr?.slice(0, 16) || ''; }
  }

  if (connected === null) return <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin h-6 w-6 text-cyan-400" /></div>;

  if (!connected) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-5 p-8">
        <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
          <Mail className="h-8 w-8 text-cyan-400/60" />
        </div>
        <div className="text-center space-y-2">
          <h2 className="text-lg font-bold text-white/80">Conectá Google</h2>
          <p className="text-sm text-white/40 max-w-sm">Autorizá a JARVIS para acceder a <b className="text-cyan-300">Gmail</b>, <b className="text-violet-300">Drive</b> y <b className="text-pink-300">Calendar</b> en un solo paso.</p>
        </div>
        <a href={`${API_BASE}/auth/google/login`}
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-white text-black font-semibold rounded-xl text-sm hover:bg-white/90 transition-all hover:scale-[1.02] active:scale-[0.98]">
          <Mail className="h-4 w-4" /> Conectar Gmail + Drive + Calendar
        </a>
      </div>
    );
  }

  if (selectedEmail) {
    return (
      <div className="flex-1 flex flex-col h-full">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.06] shrink-0 bg-white/[0.01]">
          <Button variant="ghost" size="sm" onClick={() => setSelectedEmail(null)} className="text-xs text-white/50 hover:text-white/80 gap-1.5">
            <ChevronLeft className="h-3.5 w-3.5" /> Bandeja
          </Button>
          <div className="flex-1" />
          <Button variant="ghost" size="sm" onClick={() => fetchEmailDetail(selectedEmail.id)} className="text-white/30 hover:text-white/60">
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <h2 className="text-lg font-bold text-white/90 leading-snug">{selectedEmail.subject}</h2>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <SenderAvatar from={selectedEmail.from} />
              <div>
                <p className="text-sm text-white/80 font-semibold">{selectedEmail.from.replace(/<.*>/, '').trim()}</p>
                {selectedEmail.to && <p className="text-[11px] text-white/30">para {selectedEmail.to}</p>}
              </div>
            </div>
            <div className="flex items-center gap-1.5 text-white/25 text-xs shrink-0">
              <Clock className="h-3 w-3" />
              <span>{formatEmailDate(selectedEmail.date)}</span>
            </div>
          </div>
          <div className="border-t border-white/[0.06] pt-4">
            <div className="bg-white/[0.02] rounded-xl border border-white/[0.05] p-4 text-sm text-white/65 whitespace-pre-wrap leading-[1.8] min-h-[120px]">
              {selectedEmail.body || '(el contenido no está disponible — probá actualizando)'}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const unreadCount = 0;

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Search bar */}
      <div className="p-3 pb-0 shrink-0">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/25" />
          <Input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchEmails(searchQuery)}
            placeholder="Buscar correos..."
            className="w-full bg-white/[0.04] border-white/[0.06] text-white text-sm h-10 pl-9 pr-16 rounded-xl focus:border-cyan-500/30" />
          <div className="absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-1">
            <Button onClick={() => fetchEmails(searchQuery)} size="sm" variant="ghost" disabled={loading} className="h-7 w-7 p-0">
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-400" /> : <Search className="h-3.5 w-3.5 text-white/40" />}
            </Button>
            <Button onClick={() => setShowCompose(true)} size="sm" className="h-7 px-2.5 bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 text-[11px] font-medium gap-1 rounded-lg">
              <PenLine className="h-3 w-3" /> Redactar
            </Button>
          </div>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-0.5 px-4 py-2 shrink-0">
        {FILTERS.map(f => (
          <button key={f} onClick={() => setActiveFilter(f)}
            className={cn(
              'px-3 py-1.5 text-[11px] font-medium rounded-full transition-all',
              activeFilter === f
                ? 'bg-white/10 text-white shadow-sm'
                : 'text-white/35 hover:text-white/60 hover:bg-white/[0.03]'
            )}>
            {f}
            {f === 'No leídos' && unreadCount > 0 && (
              <span className="ml-1.5 bg-cyan-500/30 text-cyan-300 px-1.5 py-0.5 rounded-full text-[9px]">{unreadCount}</span>
            )}
          </button>
        ))}
      </div>

      {error && (
        <div className="mx-4 mb-2 px-3 py-2 text-xs text-red-400 bg-red-400/5 border border-red-400/10 rounded-lg flex items-center gap-2 shrink-0">
          <AlertCircle className="h-3 w-3 shrink-0" /> {error}
        </div>
      )}

      {/* Compose modal */}
      {showCompose && (
        <div className="absolute inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-12" onClick={() => setShowCompose(false)}>
          <form onSubmit={handleSend} onClick={(e) => e.stopPropagation()}
            className="w-[95%] max-w-lg bg-[#0d0d18] border border-white/[0.08] rounded-2xl shadow-2xl p-5 space-y-3 animate-in slide-in-from-bottom-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white/80">Nuevo mensaje</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowCompose(false)} className="h-7 w-7 p-0 rounded-lg"><X className="h-4 w-4" /></Button>
            </div>
            <Input value={composeTo} onChange={(e) => setComposeTo(e.target.value)} placeholder="Para" autoFocus
              className="bg-white/[0.04] border-white/[0.06] text-white text-sm h-10 rounded-lg" />
            <Input value={composeSubject} onChange={(e) => setComposeSubject(e.target.value)} placeholder="Asunto"
              className="bg-white/[0.04] border-white/[0.06] text-white text-sm h-10 rounded-lg" />
            <textarea value={composeBody} onChange={(e) => setComposeBody(e.target.value)} placeholder="Escribí tu mensaje..." rows={8}
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg text-white text-sm p-3 resize-none focus:outline-none focus:border-cyan-500/40 placeholder:text-white/20" />
            <div className="flex justify-end gap-2">
              <Button type="submit" disabled={sending} size="sm" className="h-9 px-4 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-xs font-medium gap-1.5 rounded-lg">
                {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />} Enviar
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* Email list */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="animate-spin h-5 w-5 text-cyan-400/60" />
          </div>
        )}
        {!loading && emails.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-white/15">
            <Inbox className="h-12 w-12" />
            <p className="text-sm">{searchQuery ? `Sin resultados para "${searchQuery}"` : 'Bandeja vacía'}</p>
          </div>
        )}
        {emails.map((email) => (
          <div key={email.id} onClick={() => fetchEmailDetail(email.id)}
            className="group flex items-start gap-3 px-4 py-3 border-b border-white/[0.03] hover:bg-white/[0.03] cursor-pointer transition-colors">
            <SenderAvatar from={email.from} />
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-[13px] text-white/80 font-semibold truncate">{email.from.replace(/<.*>/, '').trim()}</p>
                <span className="text-[10px] text-white/20 tabular-nums whitespace-nowrap shrink-0">{formatEmailDate(email.date)}</span>
              </div>
              <p className="text-[12px] text-cyan-300/50 font-medium truncate mt-0.5">{email.subject || '(sin asunto)'}</p>
              <p className="text-[11px] text-white/25 truncate mt-1 leading-relaxed">{email.snippet}</p>
            </div>
            <div className="hidden group-hover:flex items-center gap-0.5 shrink-0 -mr-1">
              <button className="h-7 w-7 rounded-lg hover:bg-white/[0.06] flex items-center justify-center transition-colors" title="Archivar">
                <Archive className="h-3.5 w-3.5 text-white/25" />
              </button>
              <button className="h-7 w-7 rounded-lg hover:bg-white/[0.06] flex items-center justify-center transition-colors" title="Destacar">
                <Star className="h-3.5 w-3.5 text-white/25" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-white/[0.05] flex items-center gap-3 shrink-0 bg-white/[0.005]">
        <Button onClick={() => fetchEmails()} size="sm" variant="ghost" className="text-[11px] text-white/30 hover:text-cyan-400/60 h-7 gap-1.5">
          <RefreshCw className="h-3 w-3" /> Actualizar
        </Button>
        <span className="text-[10px] text-white/15 ml-auto">{emails.length} correos</span>
      </div>
    </div>
  );
}
