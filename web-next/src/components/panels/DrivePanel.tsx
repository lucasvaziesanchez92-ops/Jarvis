'use client';

import React, { useState, useEffect, useRef, type ChangeEvent, useCallback } from 'react';
import { Upload, Download, Trash2, Loader2, AlertCircle, FolderOpen, Search, X, Grid3X3, List, FileText, FileImage, FileAudio, FileIcon, FileCode, HardDrive } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { API_BASE } from '@/lib/api';

interface DriveItem {
  id: string; name: string; mimeType: string; size?: string; createdTime: string; webViewLink?: string;
}
type ViewMode = 'grid' | 'list';

const FOLDER_MIME = 'application/vnd.google-apps.folder';

function getFileIcon(mime: string) {
  if (mime === FOLDER_MIME) return { Icon: FolderOpen, color: 'text-amber-400/60' };
  if (mime.startsWith('image/')) return { Icon: FileImage, color: 'text-pink-400/60' };
  if (mime.startsWith('audio/')) return { Icon: FileAudio, color: 'text-purple-400/60' };
  if (mime.startsWith('video/')) return { Icon: FileIcon, color: 'text-blue-400/60' };
  if (mime === 'application/pdf') return { Icon: FileText, color: 'text-red-400/60' };
  if (mime.startsWith('text/')) return { Icon: FileText, color: 'text-cyan-400/60' };
  if (mime.includes('json') || mime.includes('javascript')) return { Icon: FileCode, color: 'text-yellow-400/60' };
  if (mime.includes('spreadsheet') || mime.includes('excel')) return { Icon: FileText, color: 'text-green-400/60' };
  if (mime.includes('document') || mime.includes('word')) return { Icon: FileText, color: 'text-blue-300/60' };
  return { Icon: FileText, color: 'text-white/40' };
}

function formatSize(s: string | undefined): string {
  if (!s) return '—'; const n = Number(s); if (isNaN(n)) return '—';
  if (n > 1073741824) return `${(n / 1073741824).toFixed(1)} GB`;
  if (n > 1048576) return `${(n / 1048576).toFixed(1)} MB`;
  if (n > 1024) return `${Math.round(n / 1024)} KB`; return `${n} B`;
}

export default function DrivePanel() {
  const [items, setItems] = useState<DriveItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [connected, setConnected] = useState<boolean | null>(null);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [view, setView] = useState<ViewMode>('grid');
  const [hasSearched, setHasSearched] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const debRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => { checkStatus(); }, []);

  async function checkStatus() {
    try {
      const res = await fetch(`${API_BASE}/auth/google/status`);
      const data = await res.json();
      setConnected(data.connected ?? false);
      if (data.connected) fetchItems();
    } catch { setConnected(false); }
  }

  const doSearch = useCallback((q: string) => {
    if (debRef.current) clearTimeout(debRef.current);
    debRef.current = setTimeout(() => fetchItems(q), 300);
  }, []);

  async function fetchItems(query: string = '') {
    setLoading(true); setError(''); setHasSearched(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/drive/list?max_results=200`);
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || 'Error'); }
      const data: DriveItem[] = await res.json();
      const filtered = query ? data.filter(f => f.name.toLowerCase().includes(query.toLowerCase())) : data;
      setItems(filtered);
    } catch (e: any) { setError(e.message); if (e.message?.includes('no está conectado')) setConnected(false); }
    finally { setLoading(false); }
  }

  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true); setError('');
    try {
      const fd = new FormData(); fd.append('file', file);
      const res = await fetch(`${API_BASE}/api/v1/drive/upload`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error('Error al subir');
      fetchItems();
    } catch (e: any) { setError(e.message); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ''; }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`¿Borrar "${name}"?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/drive/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Error al borrar');
      setItems(items.filter(f => f.id !== id));
    } catch (e: any) { setError(e.message); }
  }

  function handleDownload(id: string) {
    const a = document.createElement('a');
    a.href = `${API_BASE}/api/v1/drive/download/${id}`;
    a.download = ''; document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }

  if (connected === null) return <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin h-6 w-6 text-cyan-400" /></div>;

  if (!connected) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-5 p-8">
        <HardDrive className="h-14 w-14 text-cyan-400/30" />
        <h2 className="text-lg font-bold text-white/80">Conectá Google Drive</h2>
        <p className="text-sm text-white/40 text-center max-w-sm">Accedé a todos tus archivos desde JARVIS. Reemplaza el storage de Railway.</p>
        <a href={`${API_BASE}/auth/google/login`} className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-black font-bold rounded-xl text-sm hover:bg-white/90 transition-colors">
          <HardDrive className="h-4 w-4" /> Conectar Drive
        </a>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.05] shrink-0">
        <Input value={searchQuery} onChange={e => { setSearchQuery(e.target.value); doSearch(e.target.value); }}
          placeholder="Buscar en Drive..." className="flex-1 bg-white/[0.04] border-white/[0.08] text-white text-sm h-9 rounded-lg" />
        {searchQuery && <Button onClick={() => { setSearchQuery(''); fetchItems(); }} size="sm" variant="ghost" className="h-9 w-9 p-0"><X className="h-4 w-4" /></Button>}
        <Button onClick={() => view === 'grid' ? setView('list') : setView('grid')} size="sm" variant="ghost" className="h-9 w-9 p-0"
          title={view === 'grid' ? 'Vista lista' : 'Vista cuadrícula'}>
          {view === 'grid' ? <List className="h-4 w-4" /> : <Grid3X3 className="h-4 w-4" />}
        </Button>
        <Button onClick={() => fileRef.current?.click()} size="sm" disabled={uploading} className="h-9 px-3 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-xs gap-1.5">
          {uploading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />} Subir
        </Button>
        <input ref={fileRef} type="file" className="hidden" multiple onChange={handleUpload} />
      </div>

      {error && <div className="px-4 py-2 text-xs text-red-400 bg-red-400/5 flex items-center gap-2 shrink-0"><AlertCircle className="h-3 w-3" /> {error}</div>}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && <div className="flex items-center justify-center py-12"><Loader2 className="animate-spin h-5 w-5 text-cyan-400" /></div>}
        {!loading && items.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-white/30">
            <FolderOpen className="h-12 w-12" />
            <p className="text-sm">{hasSearched && searchQuery ? `Sin resultados para "${searchQuery}"` : 'Arrastrá archivos o hacé clic en Subir'}</p>
          </div>
        )}

        {view === 'grid'
          ? <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {items.map(f => {
                const { Icon, color } = getFileIcon(f.mimeType);
                return (
                  <div key={f.id} className="group relative bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.04] hover:border-white/[0.08] rounded-xl p-3 transition-all cursor-pointer"
                    onDoubleClick={() => f.mimeType === FOLDER_MIME ? null : handleDownload(f.id)}>
                    <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 flex gap-1 transition-opacity">
                      <button onClick={(e) => { e.stopPropagation(); handleDelete(f.id, f.name); }} className="p-1 hover:bg-red-500/20 rounded">
                        <Trash2 className="h-3 w-3 text-red-400/60" />
                      </button>
                    </div>
                    <div className="flex flex-col items-center gap-2">
                      <Icon className={`h-10 w-10 ${color}`} />
                      <p className="text-[10px] text-white/70 text-center line-clamp-2 leading-tight font-medium">{f.name}</p>
                      <span className="text-[9px] text-white/25">{formatSize(f.size)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          : <div className="space-y-1">
              {items.map(f => {
                const { Icon, color } = getFileIcon(f.mimeType);
                return (
                  <div key={f.id} className="flex items-center gap-3 px-3 py-2 hover:bg-white/[0.03] border border-transparent hover:border-white/[0.04] rounded-lg transition-all group"
                    onDoubleClick={() => f.mimeType === FOLDER_MIME ? null : handleDownload(f.id)}>
                    <Icon className={`h-5 w-5 ${color} flex-shrink-0`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-white/80 truncate">{f.name}</p>
                      <p className="text-[9px] text-white/25">{f.createdTime?.slice(0, 10)}</p>
                    </div>
                    <span className="text-[9px] text-white/20">{formatSize(f.size)}</span>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
                      <Button onClick={() => handleDownload(f.id)} size="sm" variant="ghost" className="h-7 w-7 p-0">
                        <Download className="h-3.5 w-3.5 text-cyan-400/60" />
                      </Button>
                      <Button onClick={() => handleDelete(f.id, f.name)} size="sm" variant="ghost" className="h-7 w-7 p-0">
                        <Trash2 className="h-3.5 w-3.5 text-red-400/60" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
        }
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-white/[0.05] flex items-center justify-between shrink-0">
        <Button onClick={() => fetchItems()} size="sm" variant="ghost" className="text-xs text-cyan-400/60 h-7">Actualizar</Button>
        <span className="text-[9px] text-white/20">{items.length} elementos · {items.reduce((acc, f) => acc + (Number(f.size) || 0), 0) > 0 ? formatSize(String(items.reduce((acc, f) => acc + (Number(f.size) || 0), 0))) : '—'}</span>
      </div>
    </div>
  );
}
