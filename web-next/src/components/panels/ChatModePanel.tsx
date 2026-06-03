'use client';

import React, { KeyboardEvent, useRef, useEffect, useState, ChangeEvent } from 'react';
import { Send, Bot, User, Plus, MessageSquare, Pencil, Trash2, X, History, Paperclip } from 'lucide-react';
import { useJarvisStore } from '@/store/jarvisStore';
import { useJarvisChat } from '@/hooks/useJarvisChat';
import { cn } from '@/lib/utils';

/* ── ChatModePanel v6 — Historial compacto + input grande ───────────
   Sidebar de historial colapsable, textarea ancho y alto, mensajes
   con más espacio para leer.
   ────────────────────────────────────────────────────────────────── */

export default function ChatModePanel() {
  const {
    chatMessages: messages,
    chatInput: input,
    setChatInput: setInput,
    persona,
    availablePersonas,
    setPersona,
    newConversation,
    loadConversation,
    deleteConversation,
    renameConversation,
    chatHistory,
    clearChat,
  } = useJarvisStore();

  const { sendMessage: wsSend, isConnected, status } = useJarvisChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [preUploadedAttachments, setPreUploadedAttachments] = useState<Array<{key: string, filename: string, size?: number}>>([]);
  const [uploading, setUploading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const pending = localStorage.getItem('jarvis_pending_attachment');
    if (pending) {
      try {
        const file = JSON.parse(pending);
        setPreUploadedAttachments(prev => {
          if (prev.some(f => f.key === file.key)) return prev;
          return [...prev, file];
        });
        localStorage.removeItem('jarvis_pending_attachment');
      } catch (e) {
        console.error('Error parsing pending attachment', e);
      }
    }
  }, [input]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setAttachments(prev => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const uploadAttachments = async (): Promise<Array<{key: string, filename: string, size: number, content_type: string}>> => {
    if (attachments.length === 0) return [];
    const results = [];

    for (const file of attachments) {
      const form = new FormData();
      form.append('file', file);
      form.append('folder', 'chat_attachments');
      form.append('generate_url', 'false');

      const res = await fetch('/api/files/upload', {
        method: 'POST',
        body: form,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      const data = await res.json();
      results.push({
        key: data.key,
        filename: data.filename,
        size: data.size,
        content_type: data.content_type,
      });
    }
    return results;
  };

  const sendMessage = async () => {
    const msg = input.trim();
    if (!msg && attachments.length === 0 && preUploadedAttachments.length === 0) return;

    // Show user message immediately
    const userMessage = { id: crypto.randomUUID(), role: 'user' as const, content: msg || '[Archivo adjunto]' };
    useJarvisStore.getState().appendChatMessage(userMessage);
    setInput('');

    // Upload files if any
    let uploadedFiles: Array<{key: string, filename: string}> = [...preUploadedAttachments];
    if (attachments.length > 0) {
      setUploading(true);
      try {
        const newUploaded = await uploadAttachments();
        uploadedFiles = [...uploadedFiles, ...newUploaded];
      } catch (err) {
        console.error('Upload error:', err);
        useJarvisStore.getState().appendChatMessage({
          id: crypto.randomUUID(), role: 'assistant', content: '❌ Error al subir archivo(s). Intentá de nuevo.',
        });
        setUploading(false);
        setAttachments([]);
        return;
      }
      setUploading(false);
      setAttachments([]);
    }

    setPreUploadedAttachments([]);

    // Send via WebSocket with attachments
    wsSend(msg, uploadedFiles);
  };

  const startEditing = (id: string, title: string) => {
    setEditingId(id);
    setEditTitle(title);
  };

  const saveEdit = () => {
    if (editingId && editTitle.trim()) {
      renameConversation(editingId, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  return (
    <div className="flex h-full">
      {/* ── Toggle historial (boton flotante) ── */}
      {!showHistory && (
        <button
          onClick={() => setShowHistory(true)}
          className="absolute left-[200px] top-3 z-10 p-2 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/30 hover:text-white/60 transition-all"
          title="Mostrar historial"
        >
          <History className="w-4 h-4" />
        </button>
      )}

      {/* ── Historial sidebar ── */}
      <div
        className={cn(
          'flex flex-col border-r border-white/[0.06] bg-[#080810] transition-all duration-300',
          showHistory ? 'w-48' : 'w-0 overflow-hidden'
        )}
      >
        <div className="flex h-12 items-center justify-between px-3 border-b border-white/[0.06] shrink-0">
          <span className="text-[11px] font-medium text-white/40">Historial</span>
          <button
            onClick={() => setShowHistory(false)}
            className="p-1 rounded-lg text-white/20 hover:text-white/50 hover:bg-white/[0.05]"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="px-2 py-2 shrink-0">
          <button
            onClick={newConversation}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-[12px] font-medium
                       border border-dashed border-white/[0.08] text-white/30 hover:text-cyan-300 hover:border-cyan-400/20 hover:bg-cyan-400/[0.03] transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            Nueva conversacion
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 space-y-1">
          {chatHistory.length === 0 && (
            <p className="text-[11px] text-white/15 text-center py-6 px-2">
              Las conversaciones se guardan automaticamente.
            </p>
          )}
          {chatHistory.map((conv) => (
            <div
              key={conv.id}
              className="group flex items-center gap-2 rounded-lg px-2.5 py-2 text-[12px] cursor-pointer transition-all hover:bg-white/[0.03]"
            >
              <MessageSquare className="shrink-0 w-3.5 h-3.5 text-white/20" />
              {editingId === conv.id ? (
                <input
                  autoFocus
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(); if (e.key === 'Escape') setEditingId(null); }}
                  onBlur={saveEdit}
                  className="flex-1 bg-transparent text-white/70 outline-none text-[12px] border-b border-cyan-400/30"
                />
              ) : (
                <button
                  onClick={() => loadConversation(conv.id)}
                  className="flex-1 text-left truncate text-white/40 hover:text-white/70 transition-colors"
                  title={conv.title}
                >
                  {conv.title}
                </button>
              )}
              <button
                onClick={() => startEditing(conv.id, conv.title)}
                className="opacity-0 group-hover:opacity-100 p-1 rounded text-white/15 hover:text-white/40 hover:bg-white/[0.05] transition-all"
              >
                <Pencil className="w-3 h-3" />
              </button>
              <button
                onClick={() => deleteConversation(conv.id)}
                className="opacity-0 group-hover:opacity-100 p-1 rounded text-white/15 hover:text-red-400 hover:bg-red-400/[0.05] transition-all"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Main Chat Area ── */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] shrink-0">
          <div className="flex items-center gap-2">
            {!showHistory && (
              <button
                onClick={() => setShowHistory(true)}
                className="p-1 rounded-md text-white/20 hover:text-white/40 hover:bg-white/[0.03] transition-all"
              >
                <History className="w-4 h-4" />
              </button>
            )}
            <span className="text-[10px] tracking-[0.2em] uppercase text-white/25">
              {messages.length > 0 ? `${messages.length} mensajes` : 'Chat'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-[9px] px-2 py-0.5 rounded-full ${
              isConnected
                ? 'bg-green-400/10 text-green-400/70'
                : status === 'connecting'
                  ? 'bg-amber-400/10 text-amber-400/70'
                  : 'bg-red-400/10 text-red-400/70'
            }`}>
              {isConnected ? 'Conectado' : status === 'connecting' ? 'Conectando...' : 'Offline'}
            </span>
            {messages.length > 0 && (
              <button
                onClick={clearChat}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] transition-all
                           bg-white/[0.03] border border-white/[0.08] text-white/35 hover:bg-red-400/10 hover:border-red-400/25 hover:text-red-300"
              >
                <Plus className="w-3 h-3" />
                <span>Nueva</span>
              </button>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-hide">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center opacity-25">
              <Bot className="w-10 h-10 text-cyan-400/50 mb-3" />
              <p className="text-xs text-cyan-300/50 tracking-[0.2em]">NEURAL LINK ACTIVE</p>
              <p className="text-[10px] text-white/25 mt-1">Escribe tu consulta para comenzar</p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] px-4 py-3 rounded-2xl text-[14px] leading-relaxed ${
                  msg.role === 'user'
                    ? 'glass-strong ml-auto border-l-2 border-cyan-400/30'
                    : 'glass-base mr-auto'
                }`}
              >
                <div className="flex items-center gap-1.5 mb-1">
                  {msg.role === 'assistant' ? (
                    <>
                      <Bot className="w-3.5 h-3.5 text-cyan-400/70" />
                      <span className="text-[9px] text-cyan-400/50 tracking-[0.15em]">JARVIS</span>
                    </>
                  ) : (
                    <>
                      <User className="w-3.5 h-3.5 text-white/40" />
                      <span className="text-[9px] text-white/30 tracking-[0.15em]">USER</span>
                    </>
                  )}
                </div>

                <div className={msg.role === 'user' ? 'text-white/90' : 'text-white/70'}>
                  {msg.content}
                </div>

                {msg.toolCalls && msg.toolCalls.length > 0 && (
                  <div className="mt-2 pt-1.5 border-t border-white/[0.06] space-y-1">
                    {msg.toolCalls.map((tc, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-[10px]">
                        <span className="text-cyan-400/70">{tc.output ? '✓' : '⚡'}</span>
                        <span className="text-cyan-300/60">{tc.tool}</span>
                        {tc.output && <span className="text-green-400/60">completado</span>}
                      </div>
                    ))}
                  </div>
                )}

                {msg.isStreaming && (
                  <span className="inline-block ml-1 animate-blink text-cyan-400/60">┃</span>
                )}
              </div>
            </div>
          ))}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="px-4 py-3 border-t border-white/[0.06] shrink-0">
          {availablePersonas.length > 0 && (
            <div className="flex gap-1.5 mb-2 overflow-x-auto scrollbar-hide">
              {availablePersonas.map((p) => (
                <button
                  key={p.name}
                  onClick={() => setPersona(p)}
                  className={`shrink-0 px-2.5 py-1 rounded-full text-[10px] font-medium transition-all border ${
                    persona?.name === p.name
                      ? 'bg-cyan-400/15 border-cyan-400/30 text-cyan-300'
                      : 'bg-white/[0.03] border-white/[0.06] text-white/40 hover:bg-white/[0.06]'
                  }`}
                >
                  {p.icon} {p.label}
                </button>
              ))}
            </div>
          )}

          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              {(attachments.length > 0 || preUploadedAttachments.length > 0) && (
                <div className="flex flex-wrap gap-1.5 mb-1.5 px-1">
                  {attachments.map((file, i) => (
                    <div key={`local-${i}`} className="flex items-center gap-1 bg-white/[0.06] border border-white/[0.08] rounded-lg px-2 py-1 text-[11px] text-white/50">
                      <span className="truncate max-w-[120px]">{file.name}</span>
                      <span className="text-white/20">({(file.size / 1024).toFixed(0)}KB)</span>
                      <button onClick={() => removeAttachment(i)} className="ml-1 text-white/20 hover:text-red-400">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                  {preUploadedAttachments.map((file, i) => (
                    <div key={`pre-${i}`} className="flex items-center gap-1 bg-cyan-400/10 border border-cyan-400/20 rounded-lg px-2 py-1 text-[11px] text-cyan-300">
                      <span className="truncate max-w-[120px]">{file.filename}</span>
                      {file.size && <span className="text-cyan-400/50">({(file.size / 1024).toFixed(0)}KB)</span>}
                      <span className="text-[9px] px-1 bg-cyan-400/20 rounded text-cyan-200">S3</span>
                      <button onClick={() => setPreUploadedAttachments(prev => prev.filter((_, idx) => idx !== i))} className="ml-1 text-cyan-400/50 hover:text-red-400">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex items-end gap-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={attachments.length > 0 ? "Agregá una pregunta sobre el archivo..." : "Escribí tu consulta... (Shift+Enter para nueva línea)"}
                  rows={3}
                  className="flex-1 bg-white/[0.03] border border-white/[0.08] rounded-2xl px-4 py-3 text-[14px] text-white/90 resize-none outline-none placeholder:text-white/20 focus:border-cyan-400/30 transition-all w-full"
                  style={{ minHeight: 80, maxHeight: 160, width: '100%' }}
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="flex items-center justify-center w-10 h-12 rounded-xl border border-white/[0.08] text-white/30 hover:text-white/60 hover:border-white/[0.15] transition-all shrink-0"
                  title="Adjuntar archivo"
                >
                  <Paperclip className="w-4 h-4" />
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                   accept=".pdf,.docx,.xlsx,.xls,.ods,.txt,.md,.csv,.json,.py,.js,.ts,.jsx,.tsx,.cpp,.h,.html,.css,.sql,.yaml,.yml,.xml,.jpg,.jpeg,.png,.gif,.webp,.mp3,.wav,.mp4,.mov"
                  className="hidden"
                  onChange={handleFileSelect}
                />
                <button
                  onClick={sendMessage}
                  disabled={(!input.trim() && attachments.length === 0) || uploading}
                  className="flex items-center justify-center w-12 h-12 rounded-xl btn-cyan shrink-0 disabled:opacity-30 disabled:cursor-not-allowed"
                  aria-label="Enviar mensaje"
                >
                  {uploading ? (
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white/80 rounded-full animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
