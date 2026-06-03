'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { BookOpen, Search, Loader2, AlertCircle, Link as LinkIcon, Database, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { API_BASE } from '@/lib/api';

interface WikiPage {
  id: string;
  content: string;
  title: string;
  filename: string;
  filepath: string;
  tags: string;
  links: string;
  score: number;
}

export default function WikiPanel() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<WikiPage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [stats, setStats] = useState<{ chunks: number; vault: string } | null>(null);
  const [reindexing, setReindexing] = useState(false);

  useEffect(() => { fetchStats(); }, []);

  async function fetchStats() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/wiki/health`);
      if (res.ok) {
        const data = await res.json();
        setStats({ chunks: data.chunks, vault: data.vault });
      }
    } catch { /* wiki no configurado aún */ }
  }

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setHasSearched(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/wiki/search?q=${encodeURIComponent(query)}`);
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || 'Error buscando wiki'); }
      const data = await res.json();
      setResults(data.results || []);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [query]);

  async function handleReindex() {
    setReindexing(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/v1/wiki/reindex`, { method: 'POST' });
      if (!res.ok) throw new Error('Error reindexando');
      fetchStats();
    } catch (e: any) { setError(e.message); }
    finally { setReindexing(false); }
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      <form onSubmit={handleSearch} className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.05]">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar en tu segundo cerebro..."
          className="flex-1 bg-white/[0.04] border-white/[0.08] text-white text-sm h-9 rounded-lg"
        />
        <Button type="submit" size="sm" variant="ghost" disabled={loading} className="h-9 w-9 p-0">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
        </Button>
      </form>

      {stats && (
        <div className="px-4 py-2 border-b border-white/[0.05] flex items-center justify-between text-[10px] text-white/30">
          <span className="flex items-center gap-1"><Database className="h-3 w-3" /> {stats.chunks} fragmentos indexados</span>
          <Button onClick={handleReindex} size="sm" variant="ghost" disabled={reindexing} className="h-6 text-[10px] text-cyan-400/40 hover:text-cyan-400">
            {reindexing ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
            <span className="ml-1">Reindexar</span>
          </Button>
        </div>
      )}

      {error && (
        <div className="px-4 py-2 text-xs text-red-400 bg-red-400/5 flex items-center gap-2">
          <AlertCircle className="h-3 w-3" /> {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {loading && <div className="flex items-center justify-center py-8"><Loader2 className="animate-spin h-5 w-5 text-cyan-400" /></div>}
        {!loading && results.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-white/30">
            <BookOpen className="h-10 w-10" />
            <p className="text-sm">{hasSearched ? `Sin resultados para "${query}"` : 'Buscá en tu conocimiento'}</p>
            <p className="text-xs text-white/20">JARVIS puede buscar en tus notas de Obsidian</p>
          </div>
        )}
        {results.map((page) => (
          <div key={page.id} className="px-4 py-3 border-b border-white/[0.03]">
            <p className="text-xs text-white/80 font-medium">{page.title}</p>
            <p className="text-[10px] text-white/40 mt-1 line-clamp-4 whitespace-pre-wrap">{page.content?.slice(0, 400)}</p>
            {page.tags && (
              <div className="flex flex-wrap gap-1 mt-2">
                {page.tags.split(', ').filter(Boolean).map((tag) => (
                  <span key={tag} className="px-1.5 py-0.5 bg-cyan-500/10 border border-cyan-500/20 rounded text-[8px] text-cyan-300/60">{tag}</span>
                ))}
              </div>
            )}
            {page.links && (
              <p className="flex items-center gap-1 mt-1 text-[9px] text-white/20">
                <LinkIcon className="h-2.5 w-2.5" /> {page.links.split(', ').filter(Boolean).length} enlaces wiki
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
