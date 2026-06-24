'use client';

import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import dynamic from 'next/dynamic';
import { Network, FileText, Folder, File, Search, Database, RefreshCw, Loader2, AlertCircle, PanelLeftClose, PanelLeftOpen, X } from 'lucide-react';

// Dynamic import with SSR false to prevent "window is not defined" error in Next.js
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { API_BASE } from '@/lib/api';
import { useJarvisStore } from '@/store/jarvisStore';

export default function WikiPanel() {
  const activeWikiFile = useJarvisStore((state) => state.activeWikiFile);
  const setActiveWikiFile = useJarvisStore((state) => state.setActiveWikiFile);

  const [files, setFiles] = useState<any[]>([]);
  const [graphData, setGraphData] = useState<any>({ nodes: [], links: [] });
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [viewMode, setViewMode] = useState<'text' | 'graph'>('text');
  const [search, setSearch] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  
  const [stats, setStats] = useState<{ chunks: number; vault: string } | null>(null);
  const [reindexing, setReindexing] = useState(false);
  const [previewNode, setPreviewNode] = useState<any>(null);

  const graphRef = useRef<any>(null);

  useEffect(() => {
    async function initWiki() {
      try {
        await fetch(`${API_BASE}/api/v1/wiki/lazy_load`);
      } catch (e) {
        console.error("Failed to lazy load wiki:", e);
      }
      fetchStats();
      fetchFiles();
      fetchGraph();
    }
    initWiki();
  }, []);

  useEffect(() => {
    if (activeWikiFile) {
      setSelectedFile(activeWikiFile);
      // Optional: Clear it from the store so it doesn't get stuck, 
      // but only if we want navigating away and back to reset it.
      // setActiveWikiFile(null);
    }
  }, [activeWikiFile]);

  async function fetchStats() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/wiki/health`);
      if (res.ok) {
        const data = await res.json();
        setStats({ chunks: data.chunks, vault: data.vault });
      }
    } catch {}
  }

  async function fetchFiles() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/wiki/files`);
      if (res.ok) {
        const data = await res.json();
        setFiles(data.files || []);
      }
    } catch {}
  }

  async function fetchGraph() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/wiki/graph`);
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
      }
    } catch {}
  }

  useEffect(() => {
    if (selectedFile) {
      fetch(`${API_BASE}/api/v1/wiki/file?path=${encodeURIComponent(selectedFile)}`)
        .then(r => r.json())
        .then(d => setFileContent(d.content || ''))
        .catch(console.error);
    }
  }, [selectedFile]);

  // Adjust force graph physics to reduce clustering
  useEffect(() => {
    if (viewMode === 'graph' && graphRef.current) {
      setTimeout(() => {
        if (graphRef.current) {
          graphRef.current.d3Force('charge').strength(-800); // Much stronger repulsion to prevent clutter
          graphRef.current.d3Force('link').distance(150);    // Even longer links
          // Re-heat simulation
          graphRef.current.d3ReheatSimulation();
        }
      }, 100);
    }
  }, [viewMode, graphData]);

  async function handleReindex() {
    setReindexing(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/wiki/reindex`, { method: 'POST' });
      if (res.ok) {
        fetchStats();
        fetchFiles();
        fetchGraph();
      }
    } catch {}
    finally { setReindexing(false); }
  }

  const filteredFiles = files.filter(f => f.name.toLowerCase().includes(search.toLowerCase()) || f.directory.toLowerCase().includes(search.toLowerCase()));

  // Group files by directory
  const grouped = filteredFiles.reduce((acc, file) => {
    if (!acc[file.directory]) acc[file.directory] = [];
    acc[file.directory].push(file);
    return acc;
  }, {});

  return (
    <div className="flex-1 flex flex-col h-full bg-[#050510] text-white">
      
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.05]">
        <div className="flex items-center gap-2 bg-white/5 p-1 rounded-lg">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="px-2 py-1.5 rounded text-white/50 hover:text-white hover:bg-white/10 transition-colors"
            title={sidebarOpen ? "Ocultar panel lateral" : "Mostrar panel lateral"}
          >
            {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
          </button>
          <div className="w-px h-4 bg-white/10 mx-1"></div>
          <button 
            onClick={() => setViewMode('text')}
            className={`px-3 py-1.5 rounded flex items-center gap-2 text-xs font-medium transition-colors ${viewMode === 'text' ? 'bg-cyan-500/20 text-cyan-400' : 'text-white/60 hover:text-white'}`}
          >
            <FileText className="w-4 h-4" /> Notas
          </button>
          <button 
            onClick={() => {
              setViewMode('graph');
              setPreviewNode(null);
              setTimeout(() => graphRef.current?.zoomToFit(400, 50), 100);
            }}
            className={`px-3 py-1.5 rounded flex items-center gap-2 text-xs font-medium transition-colors ${viewMode === 'graph' ? 'bg-cyan-500/20 text-cyan-400' : 'text-white/60 hover:text-white'}`}
          >
            <Network className="w-4 h-4" /> Grafo
          </button>
        </div>

        {stats && (
          <div className="flex items-center gap-4 text-[10px] text-white/30">
            <span className="flex items-center gap-1"><Database className="h-3 w-3" /> {stats.chunks} fragmentos indexados</span>
            <Button onClick={handleReindex} size="sm" variant="ghost" disabled={reindexing} className="h-6 text-[10px] text-cyan-400/40 hover:text-cyan-400">
              {reindexing ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
              <span className="ml-1">Reindexar</span>
            </Button>
          </div>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden">
        
        {/* Sidebar */}
        <div className={`border-r border-white/5 flex flex-col bg-black/20 transition-all duration-300 ${sidebarOpen ? 'w-64' : 'w-0 border-r-0 overflow-hidden opacity-0'}`}>
          <div className="p-3 border-b border-white/5 relative">
            <Search className="w-4 h-4 absolute left-6 top-6 text-white/40" />
            <input 
              type="text" 
              placeholder="Filtrar archivos..." 
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-md py-2 pl-9 pr-3 text-sm text-white focus:outline-none focus:border-cyan-500/50"
            />
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-4">
            {Object.keys(grouped).map(dir => (
              <div key={dir}>
                <h3 className="text-[10px] font-bold text-white/40 uppercase tracking-wider mb-1.5 flex items-center gap-2">
                  <Folder className="w-3 h-3" /> {dir || 'Raíz'}
                </h3>
                <div className="space-y-0.5">
                  {grouped[dir].map((f: any) => (
                    <button
                      key={f.path}
                      onClick={() => { setSelectedFile(f.path); setViewMode('text'); }}
                      className={`w-full text-left px-2 py-1.5 rounded text-xs truncate flex items-center gap-2 transition-colors ${selectedFile === f.path && viewMode === 'text' ? 'bg-cyan-500/10 text-cyan-400' : 'text-white/70 hover:bg-white/5 hover:text-white'}`}
                    >
                      <File className="w-3 h-3 opacity-50" />
                      {f.name.replace('.md', '')}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {filteredFiles.length === 0 && (
              <p className="text-xs text-white/30 text-center py-4">No se encontraron archivos.</p>
            )}
          </div>
        </div>

        {/* Main Area */}
        <div className="flex-1 relative overflow-hidden bg-[#050510]">
          {viewMode === 'text' ? (
            <div className="h-full overflow-y-auto p-8 lg:p-12 prose prose-invert prose-emerald max-w-4xl mx-auto">
              {selectedFile ? (
                <ReactMarkdown
                  components={{
                    a: ({ node, href, children, ...props }) => {
                      if (!href) return <span className="text-gray-500">{children}</span>;
                      
                      const isInternal = href.startsWith('#wikilink:') || (!href.startsWith('http') && !href.startsWith('mailto:'));
                      
                      if (isInternal) {
                        let target = decodeURIComponent(href);
                        if (target.startsWith('#wikilink:')) {
                          target = target.replace('#wikilink:', '');
                        }
                        target = target.replace('.md', '');
                        
                        return (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              const targetFile = files.find(f => f.name === `${target}.md` || f.path === `${target}.md`);
                              if (targetFile) {
                                setSelectedFile(targetFile.path);
                                setViewMode('text');
                              } else {
                                alert(`La nota "${target}" aún no existe en tu wiki.`);
                              }
                            }}
                            className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2 font-medium bg-cyan-400/10 px-1 rounded transition-colors"
                          >
                            {children}
                          </button>
                        );
                      }
                      
                      return <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline" {...props}>{children}</a>;
                    }
                  }}
                >
                  {(fileContent || '*Cargando...*').replace(/\[\[(.*?)\]\]/g, (match, p1) => `[${p1}](#wikilink:${encodeURIComponent(p1)})`)}
                </ReactMarkdown>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-white/30 space-y-4">
                  <FileText className="w-16 h-16 opacity-20" />
                  <p>Selecciona una nota para leerla</p>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full w-full">
              <ForceGraph2D
                ref={graphRef}
                graphData={graphData}
                nodeLabel={node => `
                  <div style="background: rgba(0,0,0,0.8); padding: 8px; border-radius: 4px; font-size: 12px; border: 1px solid rgba(255,255,255,0.1); max-width: 200px; white-space: normal;">
                    <strong style="color: white">${node.id}</strong>
                    ${node.tags && Array.isArray(node.tags) && node.tags.length ? `<br/><span style="color:#00d4ff; font-size: 10px;">${node.tags.join(', ')}</span>` : ''}
                    ${node.summary && node.summary !== 'N/A' ? `<br/><span style="color:#aaa; font-size: 11px;">${node.summary}</span>` : ''}
                  </div>
                `}
                nodeColor={node => {
                  if (node.id === selectedFile?.replace('.md', '')) return '#ffffff';
                  if (node.group === 'ghost') return '#333333';
                  if (node.tags && Array.isArray(node.tags)) {
                    const t = node.tags.map((tag: string) => tag.toLowerCase());
                    if (t.includes('proyecto')) return '#00d4ff';
                    if (t.includes('persona')) return '#ff00d4';
                    if (t.includes('tecnología') || t.includes('tecnologia')) return '#ffaa00';
                    if (t.includes('concepto')) return '#00ff88';
                  }
                  return '#666688';
                }}
                linkColor={() => 'rgba(255,255,255,0.1)'}
                backgroundColor="#050510"
                onNodeClick={node => setPreviewNode(node)}
                onBackgroundClick={() => setPreviewNode(null)}
                nodeCanvasObject={(node: any, ctx, globalScale) => {
                  const label = node.id;
                  const fontSize = 12/globalScale;
                  ctx.font = `${fontSize}px Sans-Serif`;
                  const textWidth = ctx.measureText(label).width;
                  const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);
                  
                  ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
                  ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);
                  
                  ctx.textAlign = 'center';
                  ctx.textBaseline = 'middle';
                  ctx.fillStyle = node.group === 'ghost' ? '#888' : '#fff';
                  if (node.id === selectedFile?.replace('.md', '').split('/').pop()) ctx.fillStyle = '#00ff88';
                  ctx.fillText(label, node.x, node.y);
                }}
              />
              
              {previewNode && (
                <div className="absolute top-6 right-6 w-80 bg-[#0a0a1a] border border-white/20 rounded-xl shadow-[0_0_40px_rgba(0,0,0,0.8)] p-5 z-50 flex flex-col gap-4 animate-in fade-in slide-in-from-right-8 duration-200">
                  <div className="flex justify-between items-start gap-2">
                    <h3 className="font-bold text-white text-lg leading-tight">{previewNode.id}</h3>
                    <button onClick={() => setPreviewNode(null)} className="text-white/40 hover:text-white transition-colors p-1 bg-white/5 rounded-md hover:bg-white/10">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  
                  {previewNode.tags && previewNode.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {previewNode.tags.map((t: string) => (
                        <span key={t} className="px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-[10px] uppercase tracking-wider">{t}</span>
                      ))}
                    </div>
                  )}
                  
                  <div className="bg-white/5 rounded-lg p-3 text-sm text-white/80 leading-relaxed border border-white/5">
                    {previewNode.summary && previewNode.summary !== 'N/A' ? (
                      previewNode.summary
                    ) : (
                      <span className="text-white/30 italic">Sin resumen detallado disponible.</span>
                    )}
                  </div>
                  
                  <Button 
                    className="w-full mt-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-lg border-0"
                    onClick={() => {
                      const file = files.find(f => f.path === `${previewNode.id}.md` || f.name === `${previewNode.id}.md` || f.name === previewNode.id);
                      if (file) {
                        setSelectedFile(file.path);
                        setViewMode('text');
                        setPreviewNode(null);
                      } else {
                        alert(`El nodo "${previewNode.id}" no tiene un archivo físico asignado, es una etiqueta o concepto agrupador.`);
                      }
                    }}
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    Abrir Nota Completa
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
