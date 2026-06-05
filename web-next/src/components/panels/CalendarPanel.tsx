'use client';

import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Loader2, AlertCircle, Clock, MapPin, CalendarDays, ChevronLeft, ChevronRight, RefreshCw, X, Video, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { API_BASE } from '@/lib/api';

interface CalendarEvent {
  id: string; summary: string; description: string; start: string; end: string; location: string; attendees: string[];
}
interface DayCell {
  date: Date; isCurrentMonth: boolean; events: CalendarEvent[];
}

const MONTH_NAMES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
const DAY_HEADERS = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];
const EVENT_COLORS = ['#22d3ee', '#a78bfa', '#34d399', '#fbbf24', '#f472b6', '#fb923c'];

function getEventColor(event: CalendarEvent): string {
  const idx = (event.summary || '').length % EVENT_COLORS.length;
  return EVENT_COLORS[idx];
}

function formatEventTime(start: string, end: string) {
  try {
    const s = new Date(start); const e = new Date(end);
    const fmt = (d: Date) => d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
    return `${fmt(s)} - ${fmt(e)}`;
  } catch { return ''; }
}

function formatDuration(start: string, end: string): string {
  try {
    const ms = new Date(end).getTime() - new Date(start).getTime();
    const mins = Math.round(ms / 60000);
    if (mins < 60) return `${mins} min`;
    const h = Math.floor(mins / 60); const m = mins % 60;
    return m > 0 ? `${h}h ${m}min` : `${h}h`;
  } catch { return ''; }
}

function isSameDay(a: Date, b: Date) { return a.toDateString() === b.toDateString(); }

export default function CalendarPanel() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [connected, setConnected] = useState<boolean | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newStart, setNewStart] = useState('');
  const [newEnd, setNewEnd] = useState('');
  const [viewMonth, setViewMonth] = useState(() => new Date());

  useEffect(() => { checkStatus(); }, []);

  async function checkStatus() {
    try {
      const res = await fetch(`${API_BASE}/auth/google/status`);
      const data = await res.json();
      setConnected(data.connected ?? false);
      if (data.connected) fetchEvents();
    } catch { setConnected(false); }
  }

  async function fetchEvents() {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API_BASE}/api/v1/calendar/events?max_results=100`);
      if (!res.ok) throw new Error('Error al cargar eventos');
      setEvents(await res.json());
    } catch (e: any) { setError(e.message); if (e.message?.includes('no está conectado')) setConnected(false); }
    finally { setLoading(false); }
  }

  function resetForm() { setNewTitle(''); setNewStart(''); setNewEnd(''); setShowCreate(false); }

  async function handleCreate() {
    if (!newTitle.trim() || !newStart || !newEnd) return;
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/v1/calendar/events`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary: newTitle, start_time: newStart, end_time: newEnd }),
      });
      if (!res.ok) throw new Error('Error al crear evento');
      resetForm(); fetchEvents();
    } catch (e: any) { setError(e.message); }
  }

  async function handleDelete(eventId: string, summary: string) {
    if (!confirm(`\u00bfBorrar "${summary}"?`)) return;
    try {
      await fetch(`${API_BASE}/api/v1/calendar/events/${eventId}`, { method: 'DELETE' });
      setEvents(events.filter(e => e.id !== eventId));
    } catch (e: any) { setError(e.message); }
  }

  function buildCalendar(): DayCell[][] {
    const year = viewMonth.getFullYear(); const month = viewMonth.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const weeks: DayCell[][] = []; let currentWeek: DayCell[] = [];
    for (let i = 0; i < firstDay; i++) {
      const d = new Date(year, month, -firstDay + i + 1);
      currentWeek.push({ date: d, isCurrentMonth: false, events: getEventsForDate(d) });
    }
    for (let day = 1; day <= daysInMonth; day++) {
      const d = new Date(year, month, day);
      currentWeek.push({ date: d, isCurrentMonth: true, events: getEventsForDate(d) });
      if (currentWeek.length === 7) { weeks.push(currentWeek); currentWeek = []; }
    }
    if (currentWeek.length > 0) {
      for (let i = currentWeek.length; i < 7; i++) {
        const d = new Date(year, month + 1, i - currentWeek.length + 1);
        currentWeek.push({ date: d, isCurrentMonth: false, events: [] });
      }
      weeks.push(currentWeek);
    }
    return weeks;
  }

  function getEventsForDate(date: Date): CalendarEvent[] {
    const ds = date.toISOString().slice(0, 10);
    return events.filter(e => e.start?.slice(0, 10) === ds);
  }

  const today = new Date();
  const isToday = (d: Date) => isSameDay(d, today);
  const weekDays = buildCalendar();

  const upcomingEvents = events
    .filter(e => new Date(e.start) >= today)
    .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime());
  const todayEvents = upcomingEvents.filter(e => isSameDay(new Date(e.start), today));
  const futureEvents = upcomingEvents.filter(e => !isSameDay(new Date(e.start), today));

  if (connected === null) return <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin h-6 w-6 text-cyan-400" /></div>;

  if (!connected) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-5 p-8">
        <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
          <CalendarDays className="h-8 w-8 text-cyan-400/60" />
        </div>
        <div className="text-center space-y-2">
          <h2 className="text-lg font-bold text-white/80">Conectá Google Calendar</h2>
          <p className="text-sm text-white/40 max-w-sm">Mirá y administrá tus eventos directamente desde JARVIS.</p>
        </div>
        <a href={`${API_BASE}/auth/google/login`}
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-white text-black font-semibold rounded-xl text-sm hover:bg-white/90 transition-all hover:scale-[1.02] active:scale-[0.98]">
          <CalendarDays className="h-4 w-4" /> Conectar Calendar
        </a>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] shrink-0">
        <div className="flex items-center gap-1">
          <Button onClick={() => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() - 1))} size="sm" variant="ghost" className="h-8 w-8 p-0 rounded-lg">
            <ChevronLeft className="h-4 w-4 text-white/50" />
          </Button>
          <h3 className="text-sm font-bold text-white/75 min-w-[130px] text-center select-none">{MONTH_NAMES[viewMonth.getMonth()]} {viewMonth.getFullYear()}</h3>
          <Button onClick={() => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1))} size="sm" variant="ghost" className="h-8 w-8 p-0 rounded-lg">
            <ChevronRight className="h-4 w-4 text-white/50" />
          </Button>
        </div>
        <div className="flex items-center gap-1.5">
          <Button onClick={() => setViewMonth(new Date())} size="sm" variant="ghost" className="text-[11px] text-cyan-400/60 hover:text-cyan-400 h-7 px-2 rounded-lg">Hoy</Button>
          <Button onClick={fetchEvents} size="sm" variant="ghost" className="h-7 w-7 p-0 rounded-lg"><RefreshCw className="h-3.5 w-3.5 text-white/30 hover:text-cyan-400/60" /></Button>
          <Button onClick={() => setShowCreate(true)} size="sm" className="h-7 px-3 text-[11px] bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 font-medium gap-1 rounded-lg">
            <Plus className="h-3 w-3" /> Evento
          </Button>
        </div>
      </div>

      {error && (
        <div className="mx-4 my-2 px-3 py-2 text-xs text-red-400 bg-red-400/5 border border-red-400/10 rounded-lg flex items-center gap-2 shrink-0">
          <AlertCircle className="h-3 w-3 shrink-0" /> {error}
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <div className="absolute inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-16" onClick={resetForm}>
          <div onClick={e => e.stopPropagation()} className="w-[92%] max-w-sm bg-[#0d0d18] border border-white/[0.08] rounded-2xl shadow-2xl p-5 space-y-3 animate-in slide-in-from-bottom-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white/80">Nuevo evento</h3>
              <Button variant="ghost" size="sm" onClick={resetForm} className="h-7 w-7 p-0 rounded-lg"><X className="h-4 w-4" /></Button>
            </div>
            <Input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Título" autoFocus
              className="bg-white/[0.04] border-white/[0.06] text-white text-sm h-10 rounded-lg" />
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1"><label className="text-[9px] text-white/25 font-medium pl-1">Inicio</label>
                <Input value={newStart} onChange={e => setNewStart(e.target.value)} type="datetime-local" className="bg-white/[0.04] border-white/[0.06] text-white text-xs h-9 rounded-lg" />
              </div>
              <div className="space-y-1"><label className="text-[9px] text-white/25 font-medium pl-1">Fin</label>
                <Input value={newEnd} onChange={e => setNewEnd(e.target.value)} type="datetime-local" className="bg-white/[0.04] border-white/[0.06] text-white text-xs h-9 rounded-lg" />
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button onClick={handleCreate} size="sm" className="flex-1 h-9 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-xs font-medium rounded-lg">Crear</Button>
              <Button onClick={resetForm} size="sm" variant="ghost" className="h-9 px-4 text-xs text-white/40 rounded-lg">Cancelar</Button>
            </div>
          </div>
        </div>
      )}

      {/* Mini calendar grid */}
      <div className="px-4 pt-3 pb-2 shrink-0">
        <div className="grid grid-cols-7 text-center mb-1">
          {DAY_HEADERS.map(d => <span key={d} className="text-[9px] text-white/20 font-semibold uppercase tracking-wider py-1">{d}</span>)}
        </div>
        <div className="grid grid-cols-7">
          {weekDays.flat().map((cell, i) => {
            const hasEvents = cell.events.length > 0;
            const colors = [...new Set(cell.events.map(e => getEventColor(e)))];
            return (
              <button key={i} onClick={() => {
                if (hasEvents) {
                  const firstDate = new Date(cell.date);
                  setViewMonth(firstDate);
                }
              }}
                className={cn(
                  'h-8 text-[11px] rounded-lg relative flex flex-col items-center justify-center transition-colors',
                  !cell.isCurrentMonth && 'opacity-20',
                  cell.isCurrentMonth && !isToday(cell.date) && 'hover:bg-white/[0.04]',
                  isToday(cell.date) && 'bg-cyan-500/20 text-cyan-300 font-bold'
                )}>
                {cell.date.getDate()}
                {hasEvents && (
                  <div className="flex gap-[1.5px] mt-0.5 absolute -bottom-0.5">
                    {colors.slice(0, 3).map((c, j) => (
                      <div key={j} className="w-1 h-1 rounded-full" style={{ backgroundColor: c }} />
                    ))}
                    {colors.length > 3 && <div className="w-1 h-1 rounded-full bg-white/20" />}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 border-t border-white/[0.04]" />

      {/* Event list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-5">
        {loading && <div className="flex items-center justify-center py-12"><Loader2 className="animate-spin h-5 w-5 text-cyan-400/60" /></div>}

        {!loading && events.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-white/12">
            <CalendarDays className="h-10 w-10" />
            <p className="text-sm">No hay eventos cargados</p>
          </div>
        )}

        {/* Today */}
        {todayEvents.length > 0 && (
          <div>
            <h4 className="text-[10px] font-bold text-cyan-400/50 uppercase tracking-widest mb-3 pl-1 sticky top-0 bg-[#0a0a14]/95 backdrop-blur-sm py-1 z-10">
              Hoy · {today.toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric', month: 'short' })}
            </h4>
            <div className="space-y-1.5">
              {todayEvents.map(event => (
                <EventCard key={event.id} event={event} onDelete={handleDelete} />
              ))}
            </div>
          </div>
        )}

        {/* Upcoming */}
        {futureEvents.length > 0 && (
          <div>
            <h4 className="text-[10px] font-bold text-white/15 uppercase tracking-widest mb-3 pl-1 sticky top-0 bg-[#0a0a14]/95 backdrop-blur-sm py-1 z-10">Próximos</h4>
            <div className="space-y-1.5">
              {futureEvents.map(event => (
                <EventCard key={event.id} event={event} onDelete={handleDelete} />
              ))}
            </div>
          </div>
        )}

        {todayEvents.length === 0 && futureEvents.length === 0 && !loading && events.length > 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-white/12">
            <CalendarDays className="h-10 w-10" />
            <p className="text-sm">Sin eventos próximos</p>
          </div>
        )}
      </div>

      {/* Footer */}
      {events.length > 0 && (
        <div className="px-4 py-2 border-t border-white/[0.05] flex items-center justify-between shrink-0 bg-white/[0.005]">
          <Button onClick={fetchEvents} size="sm" variant="ghost" className="text-[11px] text-white/30 hover:text-cyan-400/60 h-7 gap-1.5">
            <RefreshCw className="h-3 w-3" /> Actualizar
          </Button>
          <span className="text-[10px] text-white/15">{events.length} eventos</span>
        </div>
      )}
    </div>
  );
}

function EventCard({ event, onDelete }: { event: CalendarEvent; onDelete: (id: string, summary: string) => void }) {
  const color = getEventColor(event);
  const hasLocation = !!event.location;
  const hasAttendees = event.attendees && event.attendees.length > 0;
  const hasLink = event.description?.includes('http');

  return (
    <div className="group flex gap-3 p-2.5 rounded-xl hover:bg-white/[0.03] cursor-pointer transition-all border border-transparent hover:border-white/[0.04]">
      {/* Color stripe + time */}
      <div className="flex flex-col items-center gap-1 shrink-0 w-10">
        <div className="w-1 flex-1 rounded-full" style={{ backgroundColor: color }} />
        <div className="text-[9px] text-white/20 tabular-nums leading-tight text-center">
          {new Date(event.start).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-[13px] text-white/80 font-semibold truncate">{event.summary}</p>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-[10px] text-white/25 flex items-center gap-0.5">
            <Clock className="h-2.5 w-2.5" /> {formatEventTime(event.start, event.end)}
          </span>
          {hasLocation && (
            <span className="text-[10px] text-white/25 flex items-center gap-0.5 truncate">
              <MapPin className="h-2.5 w-2.5 shrink-0" /> {event.location}
            </span>
          )}
          {hasLink && <Video className="h-2.5 w-2.5 text-white/20" />}
          {hasAttendees && <Users className="h-2.5 w-2.5 text-white/20" />}
        </div>
      </div>
      {/* Actions */}
      <div className="hidden group-hover:flex items-center shrink-0">
        <button onClick={() => onDelete(event.id, event.summary)} className="h-7 w-7 rounded-lg hover:bg-red-500/15 flex items-center justify-center transition-colors">
          <Trash2 className="h-3.5 w-3.5 text-red-400/60" />
        </button>
      </div>
    </div>
  );
}
