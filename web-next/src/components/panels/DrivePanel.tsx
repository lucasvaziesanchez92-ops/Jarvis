'use client';

import React, { useState, useEffect, useRef, type ChangeEvent, useCallback } from 'react';
import { Upload, Download, Trash2, Loader2, AlertCircle, FolderOpen, Search, X, Grid3X3, List, FileText, FileImage, FileAudio, Video, FileCode, HardDrive } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { API_BASE } from '@/lib/api';

interface DriveItem {
  id: string; name: string; mimeType: string; size?: string; createdTime: string; webViewLink?: string;
}
type ViewMode = 'grid' | 'list';
const FOLDER_MIME = 'application/vnd.google-apps.folder';

const FILE_STYLES: Record<string, { icon: React.ComponentType<any>; color: string; bg: string }> = {
  folder:  { icon: FolderOpen, color: 'text-amber-400', bg: 'bg-amber-400/10' },
  image:   { icon: FileImage,  color: 'text-pink-400',  bg: 'bg-pink-400/10' },
  audio:   { icon: FileAudio,  color: 'text-purple-400',bg: 'bg-purple-400/10' },
  video:   { icon: Video,      color: 'text-blue-400',  bg: 'bg-blue-400/10' },
  pdf:     { icon: FileText,   color: 'text-red-400',   bg: 'bg-red-400/10' },
  code:    { icon: FileCode,   color: 'text-yellow-400',bg: 'bg-yellow-400/10' },
  sheet:   { icon: FileText,   color: 'text-emerald-400',bg: 'bg-emerald-400/10' },
  doc:     { icon: FileText,   color: 'text-sky-400',   bg: 'bg-sky-400/10' },
  archive: { icon: FileText,   color: 'text-orange-400',bg: 'bg-orange-400/10' },
  default: { icon: FileText,   color: 'text-white/30',  bg: 'bg-white/[0.03]' },
};

function getFileMeta(mime: string) {
  if (mime === FOLDER_MIME) return FILE_STYLES.folder;
  if (mime.startsWith('image/')) return FILE_STYLES.image;
  if (mime.startsWith('audio/')) return FILE_STYLES.audio;
  if (mime.startsWith('video/')) return FILE_STYLES.video;
  if (mime === 'application/pdf') return FILE_STYLES.pdf;
  if (mime.includes('json') || mime.includes('javascript') || mime.includes('html')) return FILE_STYLES.code;
  if (mime.includes('spreadsheet') || mime.includes('excel')) return FILE_STYLES.sheet;
  if (mime.includes('document') || mime.includes('word')) return FILE_STYLES.doc;
  if (mime.includes('zip') || mime.includes('rar') || mime.includes('tar')) return FILE_STYLES.archive;
  return FILE_STYLES.default;
}

function formatSize(s: string | undefined): string {
  if (!s) return '\u2014'; const n = Number(s); if (isNaN(n)) return '\u2014';
  if (n > 1073741824) return `${(n / 1073741824).toFixed(1)} GB`;
  if (n > 1048576) return `${(n / 1048576).toFixed(1)} MB`;
  if (n > 1024) return `${Math.round(n / 1024)} KB`; return `${n} B`;
}

function formatDate(s: string): string {
  try { return new Date(s).toLocaleDateString('es-AR', { month: 'short', day: 'numeric' }); }
  catch { return s?.slice(0, 10) || '\u2014'; }
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
  const [dragOver, setDragOver] = useState(false);
  const [previewItem, setPreviewItem] = useState<DriveItem | null>(null);
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
      setItems(query ? data.filter(f => f.name.toLowerCase().includes(query.toLowerCase())) : data);
    } catch (e: any) { setError(e.message); if (e.message?.includes('no está conectado')) setConnected(false); }
    finally { setLoading(false); }
  }

  async function handleUpload(fileObj: File) {
    setUploading(true); setError('');
    try {
      const fd = new FormData(); fd.append('file', fileObj);
      const res = await fetch(`${API_BASE}/api/v1/drive/upload`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error('Error al subir');
      fetchItems();
    } catch (e: any) { setError(e.message); }
    finally { setUploading(false); }
  }

  async function handleDelete(id: string, name: string, e?: React.MouseEvent) {
    e?.stopPropagation();
    if (!confirm(`\u00bfBorrar "${name}"?`)) return;
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

  const folders = items.filter(f => f.mimeType === FOLDER_MIME);
  const files = items.filter(f => f.mimeType !== FOLDER_MIME);
  const totalSize = items.reduce((acc, f) => acc + (Number(f.size) || 0), 0);

  if (connected === null) return <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin h-6 w-6 text-cyan-400" /></div>;

  if (!connected) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-5 p-8">
        <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
          <HardDrive className="h-8 w-8 text-cyan-400/60" />
        </div>
        <div className="text-center space-y-2">
          <h2 className="text-lg font-bold text-white/80">Conectá Google Drive</h2>
          <p className="text-sm text-white/40 max-w-sm">Accedé a tus archivos desde JARVIS. Reemplaza el storage de Railway.</p>
        </div>
        <a href={`${API_BASE}/auth/google/login`}
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-white text-black font-semibold rounded-xl text-sm hover:bg-white/90 transition-all hover:scale-[1.02] active:scale-[0.98]">
          <HardDrive className="h-4 w-4" /> Conectar Drive
        </a>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06] shrink-0">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/25" />
          <Input value={searchQuery} onChange={e => { setSearchQuery(e.target.value); doSearch(e.target.value); }}
            placeholder="Buscar en Drive..."
            className="w-full bg-white/[0.04] border-white/[0.06] text-white text-sm h-10 pl-9 pr-9 rounded-xl focus:border-cyan-500/30" />
          {searchQuery && (
            <button onClick={() => { setSearchQuery(''); fetchItems(); }} className="absolute right-2 top-1/2 -translate-y-1/2 h-7 w-7 rounded-lg hover:bg-white/[0.06] flex items-center justify-center">
              <X className="h-3.5 w-3.5 text-white/40" />
            </button>
          )}
        </div>
        <div className="flex border border-white/[0.08] rounded-lg overflow-hidden shrink-0">
          <button onClick={() => setView('grid')}
            className={cn('h-8 w-8 flex items-center justify-center transition-colors', view === 'grid' ? 'bg-white/[0.08] text-white/80' : 'text-white/25 hover:text-white/50')}>
            <Grid3X3 className="h-3.5 w-3.5" />
          </button>
          <button onClick={() => setView('list')}
            className={cn('h-8 w-8 flex items-center justify-center transition-colors', view === 'list' ? 'bg-white/[0.08] text-white/80' : 'text-white/25 hover:text-white/50')}>
            <List className="h-3.5 w-3.5" />
          </button>
        </div>
        <Button onClick={() => fileRef.current?.click()} size="sm" disabled={uploading}
          className="h-9 px-3.5 bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 text-xs font-medium gap-1.5 rounded-lg">
          {uploading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />} Subir
        </Button>
        <input ref={fileRef} type="file" className="hidden" multiple onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }} />
      </div>

      {error && (
        <div className="mx-4 mt-2 px-3 py-2 text-xs text-red-400 bg-red-400/5 border border-red-400/10 rounded-lg flex items-center gap-2 shrink-0">
          <AlertCircle className="h-3 w-3 shrink-0" /> {error}
        </div>
      )}

      {/* Content */}
      <div
        className={cn('flex-1 overflow-y-auto p-4 transition-colors', dragOver && 'bg-cyan-500/[0.03] ring-1 ring-inset ring-cyan-500/20 rounded-lg')}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault(); setDragOver(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleUpload(file);
        }}
      >
        {loading && <div className="flex items-center justify-center py-16"><Loader2 className="animate-spin h-5 w-5 text-cyan-400/60" /></div>}

        {!loading && items.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 gap-4 text-white/15">
            <FolderOpen className="h-14 w-14" />
            <p className="text-sm">{hasSearched && searchQuery ? `Sin resultados para "${searchQuery}"` : 'Arrastrá archivos o hacé clic en Subir'}</p>
          </div>
        )}

        {/* Folders section */}
        {folders.length > 0 && (
          <div className="mb-6">
            <h3 className="text-[10px] font-semibold text-white/20 uppercase tracking-widest mb-3 px-0.5">Carpetas</h3>
            {view === 'grid' ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {folders.map(f => (
                  <GridCard key={f.id} item={f} onDelete={handleDelete} onDownload={handleDownload} onOpen={() => setPreviewItem(f)} />
                ))}
              </div>
            ) : (
              <div className="space-y-0.5">
                {folders.map(f => <ListRow key={f.id} item={f} onDelete={handleDelete} onDownload={handleDownload} onOpen={() => setPreviewItem(f)} />)}
              </div>
            )}
          </div>
        )}

        {/* Files section */}
        {files.length > 0 && (
          <div>
            {folders.length > 0 && <h3 className="text-[10px] font-semibold text-white/20 uppercase tracking-widest mb-3 px-0.5">Archivos</h3>}
            {view === 'grid' ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {files.map(f => (
                  <GridCard key={f.id} item={f} onDelete={handleDelete} onDownload={handleDownload} onOpen={() => setPreviewItem(f)} />
                ))}
              </div>
            ) : (
              <div className="space-y-0.5">
                {files.map(f => <ListRow key={f.id} item={f} onDelete={handleDelete} onDownload={handleDownload} onOpen={() => setPreviewItem(f)} />)}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 border-t border-white/[0.05] flex items-center justify-between shrink-0 bg-white/[0.005]">
        <Button onClick={() => fetchItems()} size="sm" variant="ghost" className="text-[11px] text-white/30 hover:text-cyan-400/60 h-7 gap-1.5">
          <Upload className="h-3 w-3 -rotate-90" /> Actualizar
        </Button>
        <div className="flex items-center gap-2 text-[10px] text-white/20">
          <span>{items.length} elementos</span>
          {totalSize > 0 && (
            <>
              <span className="text-white/10">·</span>
              <span>{formatSize(String(totalSize))}</span>
              <div className="w-20 h-1 rounded-full bg-white/[0.04] overflow-hidden">
                <div className="h-full bg-cyan-500/20 rounded-full" style={{ width: `${Math.min(100, (totalSize / (15 * 1073741824)) * 100)}%` }} />
              </div>
              <span>{Math.round((totalSize / 1073741824) * 10) / 10} GB</span>
            </>
          )}
        </div>
      </div>

      {/* Preview Modal */}
      {previewItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-[#121212] border border-white/10 rounded-2xl w-full max-w-5xl h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-white/[0.02]">
              <div className="flex items-center gap-2">
                <div className={cn('p-1.5 rounded-lg flex items-center justify-center', getFileMeta(previewItem.mimeType).bg)}>
                  {React.createElement(getFileMeta(previewItem.mimeType).icon, { className: cn('w-4 h-4', getFileMeta(previewItem.mimeType).color) })}
                </div>
                <span className="text-sm font-medium text-white/90">{previewItem.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => handleDownload(previewItem.id)} className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/60 hover:text-white" title="Descargar">
                  <Download className="w-4 h-4" />
                </button>
                <button onClick={() => setPreviewItem(null)} className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/60 hover:text-white" title="Cerrar">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="flex-1 bg-black/40 relative overflow-hidden flex items-center justify-center">
              {previewItem.mimeType.startsWith('image/') ? (
                <img src={`${API_BASE}/api/v1/drive/download/${previewItem.id}`} alt={previewItem.name} className="max-w-full max-h-full object-contain" />
              ) : previewItem.mimeType.startsWith('video/') ? (
                <video src={`${API_BASE}/api/v1/drive/download/${previewItem.id}`} controls className="max-w-full max-h-full" />
              ) : previewItem.mimeType.startsWith('audio/') ? (
                <audio src={`${API_BASE}/api/v1/drive/download/${previewItem.id}`} controls className="w-full max-w-md" />
              ) : (
                <iframe src={`https://drive.google.com/file/d/${previewItem.id}/preview`} className="w-full h-full border-0" allow="autoplay" />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function GridCard({ item, onDelete, onDownload, onOpen }: { item: DriveItem; onDelete: (id: string, name: string, e?: React.MouseEvent) => void; onDownload: (id: string) => void; onOpen: () => void }) {
  const { icon: Icon, color, bg } = getFileMeta(item.mimeType);
  return (
    <div className="group relative bg-white/[0.015] hover:bg-white/[0.04] border border-white/[0.04] hover:border-white/[0.08] rounded-xl p-3 transition-all cursor-pointer"
      onDoubleClick={() => item.mimeType === FOLDER_MIME ? null : onOpen()}>
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 flex gap-1 transition-opacity z-10">
        <button onClick={(e) => { e.stopPropagation(); onDownload(item.id); }} className="p-1.5 hover:bg-white/[0.08] rounded-lg">
          <Download className="h-3 w-3 text-white/40" />
        </button>
        <button onClick={(e) => onDelete(item.id, item.name, e)} className="p-1.5 hover:bg-red-500/20 rounded-lg">
          <Trash2 className="h-3 w-3 text-red-400/60" />
        </button>
      </div>
      <div className={cn('aspect-square rounded-lg mb-2.5 flex items-center justify-center', bg)}>
        <Icon className={cn('h-9 w-9', color)} />
      </div>
      <p className="text-[11px] text-white/75 font-medium line-clamp-2 leading-snug mb-0.5">{item.name}</p>
      <div className="flex items-center justify-between">
        <span className="text-[9px] text-white/25">{formatSize(item.size)}</span>
        <span className="text-[9px] text-white/15">{formatDate(item.createdTime)}</span>
      </div>
    </div>
  );
}

function ListRow({ item, onDelete, onDownload, onOpen }: { item: DriveItem; onDelete: (id: string, name: string, e?: React.MouseEvent) => void; onDownload: (id: string) => void; onOpen: () => void }) {
  const { icon: Icon, color } = getFileMeta(item.mimeType);
  return (
    <div className="group flex items-center gap-3 px-3 py-2.5 hover:bg-white/[0.03] rounded-lg transition-colors cursor-pointer"
      onDoubleClick={() => item.mimeType === FOLDER_MIME ? null : onOpen()}>
      <div className={cn('h-8 w-8 rounded-lg flex items-center justify-center shrink-0', getFileMeta(item.mimeType).bg)}>
        <Icon className={cn('h-4 w-4', color)} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] text-white/75 font-medium truncate">{item.name}</p>
        <p className="text-[9px] text-white/20">{formatDate(item.createdTime)}</p>
      </div>
      <span className="text-[10px] text-white/20 tabular-nums w-16 text-right hidden sm:block">{formatSize(item.size)}</span>
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        <button onClick={() => onDownload(item.id)} className="h-7 w-7 rounded-lg hover:bg-white/[0.06] flex items-center justify-center">
          <Download className="h-3.5 w-3.5 text-white/40" />
        </button>
        <button onClick={(e) => onDelete(item.id, item.name, e)} className="h-7 w-7 rounded-lg hover:bg-red-500/15 flex items-center justify-center">
          <Trash2 className="h-3.5 w-3.5 text-red-400/60" />
        </button>
      </div>
    </div>
  );
}
