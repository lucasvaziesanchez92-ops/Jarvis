'use client';

import { useJarvisStore } from '@/store/jarvisStore';
import {
  MessageSquare, StickyNote, CheckSquare, Mic, Timer, Mail, Star, Settings, Sparkles, Calendar, FolderOpen, BookOpen
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useEffect } from 'react';

/* ── Sidebar ────────────────────────────────────────────────── */

type NavItem = {
  id: string;
  label: string;
  icon: React.ElementType;
  badge?: { text: string; variant: 'default' | 'secondary' };
};

const NAV_ITEMS: NavItem[] = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'notes', label: 'Notas', icon: StickyNote },
  { id: 'tasks', label: 'Tareas', icon: CheckSquare },
  { id: 'voice', label: 'Voz', icon: Mic },
  { id: 'timer', label: 'Timer', icon: Timer },
  { id: 'gmail', label: 'Email', icon: Mail },
  { id: 'calendar', label: 'Calendario', icon: Calendar },
  { id: 'drive', label: 'Drive', icon: FolderOpen },
  { id: 'wiki', label: 'Wiki', icon: BookOpen },
];

const BOTTOM_ITEMS: NavItem[] = [
  { id: 'personalities', label: 'Personalidades', icon: Star },
  { id: 'settings', label: 'Configuración', icon: Settings },
];

export function AppSidebar() {
  const { currentScreen, setScreen, activityState, backendStatus, setBackendStatus } = useJarvisStore();

  // Ping backend cada 10 segundos para actualizar el footer UI
  useEffect(() => {
    const ping = async () => {
      try {
        setBackendStatus('connecting');
        const res = await fetch('/health', { signal: AbortSignal.timeout(5000) });
        if (res.ok) {
          setBackendStatus('connected');
        } else {
          setBackendStatus('error');
        }
      } catch {
        setBackendStatus('disconnected');
      }
    };
    ping();
    const interval = setInterval(ping, 10000);
    return () => clearInterval(interval);
  }, [setBackendStatus]);

  const stateColors: Record<string, string> = {
    idle: 'bg-cyan-400', listening: 'bg-green-400', thinking: 'bg-amber-400',
    speaking: 'bg-cyan-300', error: 'bg-red-400', sleep: 'bg-blue-600',
  };

  const statusMeta = {
    connected: { label: 'Conectado', dot: 'bg-cyan-500', text: 'text-cyan-500/70' },
    connecting: { label: 'Conectando...', dot: 'bg-amber-400 animate-pulse', text: 'text-amber-400/70' },
    error: { label: 'Error', dot: 'bg-red-400', text: 'text-red-400/70' },
    disconnected: { label: 'Fuera de línea', dot: 'bg-white/20', text: 'text-white/30' },
  };
  const sm = statusMeta[backendStatus];

  return (
    <div className="flex h-full w-60 flex-col border-r border-border bg-[#07070e]">
      {/* Header */}
      <div className="flex h-14 items-center gap-3 px-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className={cn('h-2 w-2 rounded-full animate-pulse', stateColors[activityState] || 'bg-cyan-400')} />
          <span className="font-semibold text-sm tracking-tight">JARVIS</span>
        </div>
        <Sparkles className="ml-auto h-3.5 w-3.5 text-cyan-500/50" />
      </div>

      <ScrollArea className="flex-1 py-2">
        <div className="px-3 py-2">
          <p className="mb-2 px-2 text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground/50">
            Principal
          </p>
          {NAV_ITEMS.map((item) => (
            <Button
              key={item.id}
              variant={currentScreen === item.id ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setScreen(item.id as any)}
              className={cn(
                'w-full justify-start gap-3 mb-0.5 h-9 rounded-lg',
                currentScreen === item.id && 'bg-secondary/10 text-secondary-foreground'
              )}
            >
              <item.icon className="h-4 w-4" />
              <span className="text-sm">{item.label}</span>
              {item.badge && (
                <Badge variant="secondary" className="ml-auto h-5 px-1.5 text-[10px]">
                  {item.badge.text}
                </Badge>
              )}
            </Button>
          ))}
        </div>

        <Separator className="mx-3 my-2 w-auto opacity-50" />

        <div className="px-3 py-2">
          <p className="mb-2 px-2 text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground/50">
            Más
          </p>
          {BOTTOM_ITEMS.map((item) => (
            <Button
              key={item.id}
              variant={currentScreen === item.id ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setScreen(item.id as any)}
              className={cn(
                'w-full justify-start gap-3 mb-0.5 h-9 rounded-lg',
                currentScreen === item.id && 'bg-secondary/10 text-secondary-foreground'
              )}
            >
              <item.icon className="h-4 w-4" />
              <span className="text-sm">{item.label}</span>
            </Button>
          ))}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t border-border p-3">
        <div className="rounded-lg bg-card/50 px-3 py-2.5 text-[11px] text-muted-foreground leading-relaxed">
          Ollama Cloud · minimax-m2.7
          <div className="mt-1 flex items-center gap-1 text-[10px]">
            <div className={cn("h-1.5 w-1.5 rounded-full", sm.dot)} />
            <span className={sm.text}>{sm.label}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
