'use client';

import React, { useState, useEffect, useRef, ChangeEvent } from 'react';
import { Upload, FileText, Trash2, HelpCircle, AlertCircle, Sparkles, CheckCircle, RefreshCw, File, FileCode, FileImage, FileAudio, FolderOpen, Download, X, Image, Music } from 'lucide-react';
import { useJarvisStore } from '@/store/jarvisStore';
import { cn } from '@/lib/utils';

interface RailwayFile {
  key: string;
  size: number;
  last_modified: string;
  filename?: string;
}

const EXT_ICONS: Record<string, React.ElementType> = {
  pdf: FileText, docx: FileText, xlsx: File, xls: File, ods: File,
  txt: FileText, md: FileText, csv: File, json: FileCode,
  py: FileCode, js: FileCode, ts: FileCode, jsx: FileCode, tsx: FileCode,
  cpp: FileCode, html: FileCode, css: FileCode, sql: FileCode,
  yaml: FileCode, yml: FileCode, xml: FileCode,
  jpg: FileImage, jpeg: FileImage, png: FileImage, gif: FileImage, webp: FileImage,
  mp3: FileAudio, wav: FileAudio, mp4: File, mov: File,
};
const EXT_COLORS: Record<string, string> = {
  pdf: 'text-red-400', docx: 'text-blue-400', xlsx: 'text-green-400',
  py: 'text-yellow-400', js: 'text-yellow-300', ts: 'text-blue-300',
  json: 'text-orange-400', csv: 'text-green-300',
  jpg: 'text-pink-400', png: 'text-pink-300',
  mp3: 'text-purple-400', mp4: 'text-purple-300',
};

function getFileExt(key: string): string {
  const filename = key.split('/').pop() || key;
  return filename.split('.').pop()?.toLowerCase() || '';
}

function getFileIcon(key: string) {
  const ext = getFileExt(key);
  const Icon = EXT_ICONS[ext] || File;
  const color = EXT_COLORS[ext] || 'text-cyan-400';
  return <Icon className={`w-5 h-5 ${color}`} />;
}

function formatSize(bytes: number) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default function FilesModePanel() {
  const [files, setFiles] = useState<RailwayFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [railwayStatus, setRailwayStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { setScreen, setChatInput } = useJarvisStore();

  const checkRailway = async () => {
    try {
      const res = await fetch('/api/files/health');
      const data = await res.json();
      setRailwayStatus(data.configured ? 'connected' : 'disconnected');
    } catch {
      setRailwayStatus('disconnected');
    }
  };

  const fetchFiles = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/files/list');
      if (!res.ok) throw new Error('Error al listar archivos');
      const data = await res.json();
      setFiles(data.files || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Error al listar archivos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkRailway();
    fetchFiles();
  }, []);

  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const selectedFiles = Array.from(e.target.files);

    setUploading(true);
    setUploadSuccess(null);
    setError(null);

    let uploaded = 0;
    let failed = 0;

    for (const file of selectedFiles) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('folder', 'railway_uploads');
      formData.append('generate_url', 'true');

      try {
        const res = await fetch('/api/files/upload', { method: 'POST', body: formData });
        if (res.ok) {
          uploaded++;
        } else {
          failed++;
          const errData = await res.json().catch(() => ({}));
          if (!error) setError(errData.detail || `Error al subir ${file.name}`);
        }
      } catch {
        failed++;
      }
    }

    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';

    if (uploaded > 0) {
      setUploadSuccess(`${uploaded} archivo(s) subidos con éxito${failed > 0 ? ` (${failed} fallaron)` : ''}`);
      await fetchFiles();
      setTimeout(() => setUploadSuccess(null), 4000);
    }
  };

  const handleDeleteFile = async (key: string) => {
    if (!confirm('¿Eliminar este archivo del bucket?')) return;
    try {
      const res = await fetch(`/api/files/${encodeURIComponent(key)}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Error al eliminar');
      setFiles(prev => prev.filter(f => f.key !== key));
    } catch (err: any) {
      alert(err.message || 'No se pudo eliminar');
    }
  };

  const handleAnalyzeFile = (file: RailwayFile) => {
    const filename = file.key.split('/').pop() || file.key;
    const attachment = {
      key: file.key,
      filename: filename,
      size: file.size,
      content_type: 'application/octet-stream',
    };
    localStorage.setItem('jarvis_pending_attachment', JSON.stringify(attachment));
    setScreen('chat');
    setChatInput(`Analizá este archivo: "${filename}". Dame un resumen detallado de su contenido.`);
  };

  const handleDownloadFile = async (file: RailwayFile) => {
    window.open(`/api/files/download/${encodeURIComponent(file.key)}`, '_blank');
  };

  return (
    <div className="flex flex-col h-full p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.06] pb-3 shrink-0">
        <div>
          <h2 className="text-base font-bold text-white tracking-wide">Railway Storage</h2>
          <div className="flex items-center gap-2 mt-0.5">
            <div className={cn(
              "w-1.5 h-1.5 rounded-full",
              railwayStatus === 'connected' ? 'bg-green-400 shadow-[0_0_6px_#4ade80]' :
              railwayStatus === 'checking' ? 'bg-amber-400 animate-pulse' : 'bg-red-400'
            )} />
            <p className="text-[10px] text-white/40">
              {railwayStatus === 'connected' ? 'Bucket conectado' :
               railwayStatus === 'checking' ? 'Verificando bucket...' : 'Bucket offline'}
            </p>
          </div>
        </div>
        <button
          onClick={() => { fetchFiles(); checkRailway(); }}
          className="p-2 rounded-xl bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.06] text-white/50 active:scale-95 transition-all"
          title="Refrescar"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Upload Zone */}
      <div
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "border border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center space-y-2",
          uploading
            ? "border-cyan-400/50 bg-cyan-400/[0.02]"
            : "border-white/[0.1] bg-white/[0.02] hover:border-cyan-400/30 hover:bg-white/[0.04]"
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          multiple
          onChange={handleFileUpload}
          accept=".pdf,.docx,.xlsx,.xls,.ods,.txt,.md,.csv,.json,.py,.js,.ts,.jsx,.tsx,.cpp,.h,.html,.css,.sql,.yaml,.yml,.xml,.jpg,.jpeg,.png,.gif,.webp,.mp3,.wav,.mp4,.mov"
          disabled={uploading}
        />
        {uploading ? (
          <>
            <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mb-1" />
            <p className="text-xs text-cyan-300 font-medium">Subiendo al bucket de Railway...</p>
            <p className="text-[10px] text-white/30">No cierres esta ventana</p>
          </>
        ) : (
          <>
            <div className="p-3 bg-cyan-400/10 rounded-full text-cyan-400 group-hover:scale-110 transition-transform">
              <Upload className="w-6 h-6" />
            </div>
            <p className="text-xs text-white/80 font-semibold">Subir archivos al bucket</p>
            <p className="text-[10px] text-white/30">
              PDF, Word, Excel, código, imágenes, CSV, JSON (múltiples, máx. 50MB c/u)
            </p>
          </>
        )}
      </div>

      {/* Messages */}
      {uploadSuccess && (
        <div className="flex items-center gap-2 bg-green-500/10 border border-green-500/20 text-green-400 rounded-xl p-3 text-xs animate-fade-in">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{uploadSuccess}</span>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-300 rounded-xl p-3 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="flex-1 leading-snug">{error}</span>
          <button onClick={() => setError(null)} className="text-amber-300/50 hover:text-amber-300">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Files List */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-0.5">
        <h3 className="text-[10px] tracking-wider uppercase text-white/30 font-semibold px-1">
          Archivos en el bucket ({files.length})
        </h3>

        {loading ? (
          <div className="space-y-2 py-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 rounded-xl bg-white/[0.02] border border-white/[0.04] animate-pulse" />
            ))}
          </div>
        ) : files.length === 0 ? (
          <div className="text-center py-12 border border-white/[0.04] rounded-2xl bg-white/[0.01]">
            <FolderOpen className="w-8 h-8 text-white/10 mx-auto mb-2" />
            <p className="text-xs text-white/30">Bucket vacío</p>
            <p className="text-[10px] text-white/20 mt-1">Subí archivos para que JARVIS los analice</p>
          </div>
        ) : (
          files.map((file) => {
            const filename = file.key.split('/').pop() || file.key;
            return (
              <div
                key={file.key}
                className="glass-base rounded-2xl p-3 flex items-center justify-between gap-3 group hover:glass-hover transition-all"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2 bg-white/[0.03] rounded-xl border border-white/[0.06] shrink-0">
                    {getFileIcon(file.key)}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-white/90 truncate pr-2" title={filename}>
                      {filename}
                    </p>
                    <div className="flex items-center gap-2 text-[10px] text-white/30 mt-0.5">
                      <span>{formatSize(file.size)}</span>
                      <span>•</span>
                      <span className="truncate max-w-[100px]">
                        {new Date(file.last_modified).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <button
                    onClick={() => handleAnalyzeFile(file)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-[10px] font-bold text-cyan-300 bg-cyan-400/10 hover:bg-cyan-400/20 active:scale-95 transition-all border border-cyan-400/20"
                    title="Analizar con IA"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Analizar</span>
                  </button>
                  <button
                    onClick={() => handleDownloadFile(file)}
                    className="p-2 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.06] text-white/20 hover:text-cyan-400 active:scale-95 transition-all opacity-0 group-hover:opacity-100"
                    title="Descargar"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleDeleteFile(file.key)}
                    className="p-2 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-red-500/10 hover:border-red-500/20 text-white/20 hover:text-red-400 active:scale-95 transition-all opacity-0 group-hover:opacity-100"
                    title="Eliminar"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
