'use client';

import React, { useState, useEffect, useRef, ChangeEvent } from 'react';
import { Upload, FileText, Trash2, AlertCircle, Sparkles, CheckCircle, RefreshCw, File, FileCode, FileImage, FileAudio, FolderOpen, Download, X, Image } from 'lucide-react';
import { useJarvisStore } from '@/store/jarvisStore';
import { cn } from '@/lib/utils';
import { API_BASE } from '@/lib/api';

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
  const [previewFile, setPreviewFile] = useState<RailwayFile | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewText, setPreviewText] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const previewAbortRef = useRef<AbortController | null>(null);
  const { setScreen, setChatInput } = useJarvisStore();

  const checkRailway = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/files/health`);
      const data = await res.json();
      setRailwayStatus(data.configured ? 'connected' : 'disconnected');
    } catch {
      setRailwayStatus('disconnected');
    }
  };

  const fetchFiles = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/v1/files/list`);
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
        const res = await fetch(`${API_BASE}/api/v1/files/upload`, { method: 'POST', body: formData });
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
      const res = await fetch(`${API_BASE}/api/v1/files/${encodeURIComponent(key)}`, { method: 'DELETE' });
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

  const handlePreviewFile = async (file: RailwayFile) => {
    // Cancel any in-flight preview request to avoid races
    if (previewAbortRef.current) previewAbortRef.current.abort();
    const abort = new AbortController();
    previewAbortRef.current = abort;

    setPreviewFile(file);
    setPreviewUrl(null);
    setPreviewText(null);

    const ext = getFileExt(file.key);
    const filename = file.key.split('/').pop() || file.key;

    // Previews directos (browser nativo): img / video / audio / pdf
    const directExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'mp4', 'webm', 'mov', 'mp3', 'wav', 'ogg', 'pdf'];
    if (directExts.includes(ext)) {
      setPreviewUrl(`${API_BASE}/api/v1/files/download/${encodeURIComponent(file.key)}`);
      return;
    }

    // Previews de texto/código: fetch el contenido y mostrar con syntax highlight
    const textExts = ['txt', 'md', 'markdown', 'json', 'xml', 'html', 'htm', 'css', 'scss',
                      'py', 'js', 'jsx', 'ts', 'tsx', 'cpp', 'h', 'hpp', 'sql',
                      'yaml', 'yml', 'log', 'env', 'cfg', 'ini', 'toml', 'csv', 'sh', 'bash'];
    if (textExts.includes(ext)) {
      try {
        const res = await fetch(`${API_BASE}/api/v1/files/download/${encodeURIComponent(file.key)}`, {
          signal: abort.signal,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const text = await res.text();
        if (abort.signal.aborted) return;
        // Cap en 200KB para no reventar el browser con un dump de 50MB
        const truncated = text.length > 200_000;
        setPreviewText(truncated ? text.slice(0, 200_000) + '\n\n... (truncado, archivo >200KB)' : text);
      } catch (e: any) {
        if (e.name === 'AbortError') return;
        setError(`No se pudo leer el archivo: ${e.message}`);
        setPreviewFile(null);
      }
      return;
    }

    // Office y otros (docx, xlsx, pptx, etc.): Google Docs Viewer via URL firmada
    try {
      const res = await fetch(`${API_BASE}/api/v1/files/url/${encodeURIComponent(file.key)}`, {
        signal: abort.signal,
      });
      if (abort.signal.aborted) return;
      if (res.ok) {
        const data = await res.json();
        setPreviewUrl(`https://docs.google.com/gview?url=${encodeURIComponent(data.url)}&embedded=true`);
      } else {
        alert('No se pudo generar vista previa para este tipo de archivo.');
        setPreviewFile(null);
      }
    } catch (e: any) {
      if (e.name === 'AbortError') return;
      alert('Error de conexión al generar vista previa.');
      setPreviewFile(null);
    }
  };

  const closePreview = () => {
    if (previewAbortRef.current) previewAbortRef.current.abort();
    setPreviewFile(null);
    setPreviewUrl(null);
    setPreviewText(null);
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
                    onClick={() => handlePreviewFile(file)}
                    className="p-2 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.06] text-white/20 hover:text-cyan-400 active:scale-95 transition-all opacity-0 group-hover:opacity-100"
                    title="Previsualizar"
                  >
                    <Image className="w-3.5 h-3.5" />
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

      {/* Preview Modal */}
      {previewFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-[#121212] border border-white/10 rounded-2xl w-full max-w-5xl h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-white/[0.02]">
              <div className="flex items-center gap-2 min-w-0">
                <div className="p-1.5 bg-white/[0.03] rounded-lg border border-white/[0.06] shrink-0">
                  {getFileIcon(previewFile.key)}
                </div>
                <span className="text-sm font-medium text-white/90 truncate max-w-[300px]">{previewFile.key.split('/').pop() || previewFile.key}</span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button onClick={() => handleDownloadFile(previewFile)} className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/60 hover:text-white" title="Descargar">
                  <Download className="w-4 h-4" />
                </button>
                <button onClick={closePreview} className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/60 hover:text-white" title="Cerrar">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="flex-1 bg-black/40 relative overflow-hidden flex items-center justify-center">
              {previewText !== null ? (
                <CodePreview text={previewText} filename={previewFile.key} />
              ) : !previewUrl ? (
                <div className="flex items-center gap-2 text-white/40">
                  <RefreshCw className="w-4 h-4 animate-spin" /> Cargando vista previa...
                </div>
              ) : getFileExt(previewFile.key).match(/^(jpg|jpeg|png|gif|webp|svg)$/i) ? (
                <img src={previewUrl} alt="Preview" className="max-w-full max-h-full object-contain" />
              ) : getFileExt(previewFile.key).match(/^(mp4|webm|mov)$/i) ? (
                <video src={previewUrl} controls className="max-w-full max-h-full" />
              ) : getFileExt(previewFile.key).match(/^(mp3|wav|ogg)$/i) ? (
                <audio src={previewUrl} controls className="w-full max-w-md" />
              ) : getFileExt(previewFile.key).match(/^(pdf)$/i) ? (
                <iframe src={previewUrl} className="w-full h-full border-0 bg-white" />
              ) : previewUrl.includes('docs.google.com') ? (
                <iframe src={previewUrl} className="w-full h-full border-0 bg-white" />
              ) : (
                <iframe src={previewUrl} className="w-full h-full border-0 bg-[#1e1e1e]" />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── CodePreview — lightweight syntax highlighter (no external libs) ── */
// Detects language by extension, applies minimal regex-based highlighting.
// Evita deps pesadas (Prism, Shiki) para mantener el bundle chico.
const LANG_KEYWORDS: Record<string, RegExp> = {
  js:   /\b(const|let|var|function|return|if|else|for|while|class|import|export|from|as|async|await|new|try|catch|throw|this|null|undefined|true|false)\b/g,
  jsx:  /\b(const|let|var|function|return|if|else|for|while|class|import|export|from|as|async|await|new|try|catch|throw|null|undefined|true|false)\b/g,
  ts:   /\b(const|let|var|function|return|if|else|for|while|class|import|export|from|as|async|await|new|try|catch|throw|interface|type|enum|public|private|protected|readonly|null|undefined|true|false)\b/g,
  tsx:  /\b(const|let|var|function|return|if|else|for|while|class|import|export|from|as|async|await|new|try|catch|throw|interface|type|enum|public|private|protected|readonly|null|undefined|true|false)\b/g,
  py:   /\b(def|class|import|from|as|return|if|elif|else|for|while|try|except|finally|with|lambda|yield|pass|break|continue|None|True|False|and|or|not|in|is|self)\b/g,
  css:  /\b(import|url|@media|@keyframes|@font-face|from|to|important)\b/g,
  json: /\b(true|false|null)\b/g,
  sql:  /\b(SELECT|FROM|WHERE|INSERT|INTO|VALUES|UPDATE|SET|DELETE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AS|GROUP|ORDER|BY|LIMIT|OFFSET|CREATE|TABLE|INDEX|DROP|ALTER|ADD|PRIMARY|KEY|FOREIGN|REFERENCES|NULL|NOT|AND|OR|IN|LIKE|BETWEEN)\b/gi,
  yaml: /\b(true|false|null|yes|no|on|off)\b/g,
};

function highlightCode(text: string, ext: string): string {
  // 1. Escape HTML
  let s = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // 2. Strings (single, double, backtick)
  s = s.replace(/(`[^`\n]*`|"[^"\n]*"|'[^'\n]*')/g, '<span class="text-amber-300">$1</span>');

  // 3. Comments
  if (['js', 'jsx', 'ts', 'tsx', 'css'].includes(ext)) {
    s = s.replace(/(\/\/[^\n]*|\/\*[\s\S]*?\*\/)/g, '<span class="text-white/30 italic">$1</span>');
  } else if (['py', 'sql', 'yaml'].includes(ext)) {
    s = s.replace(/(#[^\n]*)/g, '<span class="text-white/30 italic">$1</span>');
  }

  // 4. Numbers
  s = s.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="text-purple-300">$1</span>');

  // 5. Keywords (per-language)
  const kw = LANG_KEYWORDS[ext];
  if (kw) {
    s = s.replace(kw, '<span class="text-cyan-300 font-semibold">$&</span>');
  }

  return s;
}

function CodePreview({ text, filename }: { text: string; filename: string }) {
  const ext = getFileExt(filename);
  const isCode = !!LANG_KEYWORDS[ext];
  const lines = text.split('\n');

  return (
    <div className="w-full h-full overflow-auto bg-[#0d0d0d] p-4 font-mono text-[12px] leading-relaxed">
      <div className="flex gap-3">
        {/* Line numbers gutter */}
        <div className="select-none text-right text-white/20 shrink-0">
          {lines.map((_, i) => (
            <div key={i} className="px-2">{i + 1}</div>
          ))}
        </div>
        {/* Code */}
        <pre className="flex-1 text-white/85 whitespace-pre-wrap break-all m-0">
          {isCode ? (
            <code dangerouslySetInnerHTML={{ __html: highlightCode(text, ext) }} />
          ) : (
            <code>{text}</code>
          )}
        </pre>
      </div>
    </div>
  );
}
