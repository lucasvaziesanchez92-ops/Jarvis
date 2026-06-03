'use client';

import React, { useState, useEffect } from 'react';
import { Mail, Search, Loader2, AlertCircle, Clock, ChevronLeft, Send, X, PenLine, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { API_BASE } from '@/lib/api';

interface EmailItem {
  id: string; thread_id: string; from: string; subject: string; date: string; snippet: string;
}
interface EmailDetail extends EmailItem { to: string; body: string; }

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
      const data = await res.json();
      setEmails(data);
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
        <Mail className="h-14 w-14 text-cyan-400/30" />
        <h2 className="text-lg font-bold text-white/80">Conectá Gmail</h2>
        <p className="text-sm text-white/40 text-center max-w-sm">Autorizá a JARVIS para acceder y enviar correos desde tu cuenta de Google.</p>
        <a href={`${API_BASE}/auth/google/login`} className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-black font-bold rounded-xl text-sm hover:bg-white/90 transition-colors">
          <Mail className="h-4 w-4" /> Conectar Gmail
        </a>
      </div>
    );
  }

  if (selectedEmail) {
    return (
      <div className="flex-1 flex flex-col h-full">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.05] shrink-0">
          <Button variant="ghost" size="sm" onClick={() => setSelectedEmail(null)} className="text-xs flex items-center gap-1">
            <ChevronLeft className="h-3.5 w-3.5" /> Bandeja
          </Button>
          <div className="flex-1" />
          <Button variant="ghost" size="sm" onClick={() => fetchEmailDetail(selectedEmail.id)}>
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <h2 className="text-base font-bold text-white/90 leading-snug">{selectedEmail.subject}</h2>
          <div className="flex flex-col gap-1 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-white/70 font-semibold">{selectedEmail.from.split('<')[0]?.trim() || selectedEmail.from}</span>
              <div className="flex items-center gap-1 text-white/30">
                <Clock className="h-3 w-3" />
                <span>{formatEmailDate(selectedEmail.date)}</span>
              </div>
            </div>
            {selectedEmail.to && <span className="text-[11px] text-white/40">para {selectedEmail.to}</span>}
          </div>
          <div className="border-t border-white/[0.05] pt-4">
            <div className="bg-white/[0.02] rounded-xl border border-white/[0.06] p-4 text-sm text-white/70 whitespace-pre-wrap leading-[1.7] min-h-[100px]">
              {selectedEmail.body || '(el contenido no está disponible — probá actualizando)'}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header: search + compose */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.05] shrink-0">
        <Input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchEmails(searchQuery)}
          placeholder="Buscar correos..."
          className="flex-1 bg-white/[0.04] border-white/[0.08] text-white text-sm h-9 rounded-lg" />
        <Button onClick={() => fetchEmails(searchQuery)} size="sm" variant="ghost" disabled={loading} className="h-9 w-9 p-0">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
        </Button>
        <Button onClick={() => setShowCompose(true)} size="sm" className="h-9 px-3 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-xs gap-1.5">
          <PenLine className="h-3.5 w-3.5" /> Redactar
        </Button>
      </div>

      {error && <div className="px-4 py-2 text-xs text-red-400 bg-red-400/5 flex items-center gap-2 shrink-0"><AlertCircle className="h-3 w-3" /> {error}</div>}

      {/* Compose modal */}
      {showCompose && (
        <div className="absolute inset-0 z-50 bg-black/60 flex items-start justify-center pt-12" onClick={() => setShowCompose(false)}>
          <form onSubmit={handleSend} onClick={(e) => e.stopPropagation()}
            className="w-[95%] max-w-lg bg-[#0d0d18] border border-white/[0.08] rounded-xl shadow-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white/80">Nuevo mensaje</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowCompose(false)} className="h-7 w-7 p-0"><X className="h-4 w-4" /></Button>
            </div>
            <Input value={composeTo} onChange={(e) => setComposeTo(e.target.value)} placeholder="Para" autoFocus
              className="bg-white/[0.04] border-white/[0.08] text-white text-sm h-9" />
            <Input value={composeSubject} onChange={(e) => setComposeSubject(e.target.value)} placeholder="Asunto"
              className="bg-white/[0.04] border-white/[0.08] text-white text-sm h-9" />
            <textarea value={composeBody} onChange={(e) => setComposeBody(e.target.value)} placeholder="Escribí tu mensaje..." rows={8}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm p-3 resize-none focus:outline-none focus:border-cyan-500/40" />
            <div className="flex justify-end gap-2">
              <Button type="submit" disabled={sending} size="sm" className="h-8 px-4 bg-cyan-500/30 hover:bg-cyan-500/40 text-xs gap-1.5">
                {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />} Enviar
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* Inbox */}
      <div className="flex-1 overflow-y-auto">
        {loading && <div className="flex items-center justify-center py-12"><Loader2 className="animate-spin h-5 w-5 text-cyan-400" /></div>}
        {!loading && emails.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-white/30">
            <Mail className="h-10 w-10" />
            <p className="text-sm">{searchQuery ? `Sin resultados para "${searchQuery}"` : 'Bandeja vacía'}</p>
          </div>
        )}
        {emails.map((email) => (
          <div key={email.id} onClick={() => fetchEmailDetail(email.id)}
            className="flex items-start gap-3 px-4 py-3 border-b border-white/[0.03] hover:bg-white/[0.02] cursor-pointer transition-colors">
            <div className="w-8 h-8 rounded-full bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-[10px] font-bold text-cyan-300/70">{(email.from || '?')[0].toUpperCase()}</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs text-white/85 font-semibold truncate">{email.from.replace(/<.*>/, '').trim()}</p>
                <span className="text-[9px] text-white/25 whitespace-nowrap">{formatEmailDate(email.date)}</span>
              </div>
              <p className="text-xs text-cyan-300/60 font-medium truncate mt-0.5">{email.subject || '(sin asunto)'}</p>
              <p className="text-[10px] text-white/30 truncate mt-1 leading-relaxed">{email.snippet}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="px-4 py-2 border-t border-white/[0.05] flex items-center gap-2 shrink-0">
        <Button onClick={() => fetchEmails()} size="sm" variant="ghost" className="text-xs text-cyan-400/60 hover:text-cyan-400 h-7">
          <RefreshCw className="h-3 w-3 mr-1" /> Actualizar
        </Button>
        <span className="text-[9px] text-white/20 ml-auto">{emails.length} correos</span>
      </div>
    </div>
  );
}
