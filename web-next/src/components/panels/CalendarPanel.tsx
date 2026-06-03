'use client';

import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Loader2, AlertCircle, Clock, MapPin, CalendarDays, ChevronLeft, ChevronRight, RefreshCw, X } from 'lucide-react';
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
const DAY_NAMES = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];

export default function CalendarPanel() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [connected, setConnected] = useState<boolean | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newStart, setNewStart] = useState('');
  const [newEnd, setNewEnd] = useState('');
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
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
      const monthStart = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), 1);
      const monthEnd = new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 0);
      const res = await fetch(`${API_BASE}/api/v1/calendar/events?max_results=100`);
      if (!res.ok) throw new Error('Error fetching events');
      setEvents(await res.json());
    } catch (e: any) { setError(e.message); if (e.message?.includes('no está conectado')) setConnected(false); }
    finally { setLoading(false); }
  }

  function resetForm() { setNewTitle(''); setNewStart(''); setNewEnd(''); setShowCreate(false); }

  async function handleCreate() {
    if (!newTitle.trim() || !newStart || !newEnd) return;
    setError('');
    try {
      await fetch(`${API_BASE}/api/v1/calendar/events`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary: newTitle, start_time: newStart, end_time: newEnd }),
      });
      resetForm(); fetchEvents();
    } catch (e: any) { setError(e.message); }
  }

  async function handleDelete(eventId: string, summary: string) {
    if (!confirm(`¿Borrar "${summary}"?`)) return;
    try {
      await fetch(`${API_BASE}/api/v1/calendar/events/${eventId}`, { method: 'DELETE' });
      setEvents(events.filter(e => e.id !== eventId));
    } catch (e: any) { setError(e.message); }
  }

  function buildCalendar(): DayCell[][] {
    const year = viewMonth.getFullYear();
    const month = viewMonth.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const weeks: DayCell[][] = [];
    let currentWeek: DayCell[] = [];

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

  function formatEventTime(e: CalendarEvent) {
    try {
      const s = new Date(e.start);
      const en = new Date(e.end);
      const timeStr = s.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
      return `${timeStr}`;
    } catch { return ''; }
  }

  const today = new Date();
  const isToday = (d: Date) => d.toDateString() === today.toDateString();
  const weekDays = buildCalendar();

  if (connected === null) return <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin h-6 w-6 text-cyan-400" /></div>;

  if (!connected) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-5 p-8">
        <CalendarDays className="h-14 w-14 text-cyan-400/30" />
        <h2 className="text-lg font-bold text-white/80">Conectá Google Calendar</h2>
        <p className="text-sm text-white/40 text-center max-w-sm">Mirá y administrá tus eventos desde JARVIS.</p>
        <a href={`${API_BASE}/auth/google/login`} className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-black font-bold rounded-xl text-sm hover:bg-white/90">
          <CalendarDays className="h-4 w-4" /> Conectar Calendar
        </a>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.05] shrink-0">
        <div className="flex items-center gap-2">
          <Button onClick={() => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() - 1))} size="sm" variant="ghost" className="h-8 w-8 p-0"><ChevronLeft className="h-4 w-4" /></Button>
          <h3 className="text-sm font-bold text-white/80 min-w-[120px] text-center">{MONTH_NAMES[viewMonth.getMonth()]} {viewMonth.getFullYear()}</h3>
          <Button onClick={() => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1))} size="sm" variant="ghost" className="h-8 w-8 p-0"><ChevronRight className="h-4 w-4" /></Button>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setViewMonth(new Date())} size="sm" variant="ghost" className="text-xs text-cyan-400/60 h-7">Hoy</Button>
          <Button onClick={fetchEvents} size="sm" variant="ghost" className="h-7 w-7 p-0"><RefreshCw className="h-3.5 w-3.5 text-cyan-400/60" /></Button>
          <Button onClick={() => setShowCreate(true)} size="sm" className="h-8 px-3 text-xs bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 gap-1"><Plus className="h-3.5 w-3.5" /> Evento</Button>
        </div>
      </div>

      {error && <div className="px-4 py-2 text-xs text-red-400 bg-red-400/5 flex items-center gap-2 shrink-0"><AlertCircle className="h-3 w-3" /> {error}</div>}

      {/* Create modal */}
      {showCreate && (
        <div className="absolute inset-0 z-50 bg-black/60 flex items-start justify-center pt-16" onClick={resetForm}>
          <div onClick={e => e.stopPropagation()} className="w-[90%] max-w-sm bg-[#0d0d18] border border-white/[0.08] rounded-xl shadow-2xl p-5 space-y-3">
            <div className="flex items-center justify-between"><h3 className="text-sm font-bold text-white/80">Nuevo evento</h3><Button variant="ghost" size="sm" onClick={resetForm} className="h-7 w-7 p-0"><X className="h-4 w-4" /></Button></div>
            <Input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Título" autoFocus className="bg-white/[0.04] border-white/[0.08] text-white text-sm h-9" />
            <div className="flex gap-2">
              <Input value={newStart} onChange={e => setNewStart(e.target.value)} type="datetime-local" className="flex-1 bg-white/[0.04] border-white/[0.08] text-white text-xs h-9" />
              <Input value={newEnd} onChange={e => setNewEnd(e.target.value)} type="datetime-local" className="flex-1 bg-white/[0.04] border-white/[0.08] text-white text-xs h-9" />
            </div>
            <div className="flex gap-2"><Button onClick={handleCreate} size="sm" className="flex-1 h-8 bg-cyan-500/30 text-xs">Crear</Button><Button onClick={resetForm} size="sm" variant="ghost" className="h-8 text-xs">Cancelar</Button></div>
          </div>
        </div>
      )}

      {/* Calendar Grid */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Day headers */}
        <div className="grid grid-cols-7 border-b border-white/[0.04] shrink-0">
          {DAY_NAMES.map(d => <div key={d} className="py-2 text-center text-[10px] text-white/25 font-semibold uppercase tracking-wider">{d}</div>)}
        </div>
        {/* Weeks */}
        <div className="flex-1 grid grid-rows-6 overflow-hidden">
          {loading && <div className="absolute inset-0 flex items-center justify-center bg-black/20 z-10"><Loader2 className="animate-spin h-5 w-5 text-cyan-400" /></div>}
          {weekDays.map((week, wi) => (
            <div key={wi} className="grid grid-cols-7 border-b border-white/[0.02]">
              {week.map((cell, ci) => {
                const hasEvents = cell.events.length > 0;
                return (
                  <div key={ci} onClick={() => setSelectedDate(hasEvents ? cell.date : null)}
                    className={`relative p-1 border-r border-white/[0.02] text-center cursor-pointer hover:bg-white/[0.02] transition-colors min-h-[40px] flex flex-col items-center ${
                      !cell.isCurrentMonth ? 'opacity-25' : ''}`}>
                    <span className={`text-[11px] font-medium ${
                      isToday(cell.date) ? 'w-5 h-5 rounded-full bg-cyan-500/30 text-cyan-300 flex items-center justify-center' : 'text-white/50'}`}>
                      {cell.date.getDate()}
                    </span>
                    {hasEvents && (
                      <div className="flex gap-0.5 mt-0.5">
                        {cell.events.slice(0, 3).map((e, i) => (
                          <div key={i} className="w-1 h-1 rounded-full bg-cyan-400/60" title={e.summary} />
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Upcoming events list */}
      {!loading && events.length > 0 && (
        <div className="border-t border-white/[0.05] max-h-[140px] overflow-y-auto shrink-0">
          <p className="px-4 pt-2 pb-1 text-[10px] text-white/20 font-semibold uppercase tracking-wider">Próximos eventos</p>
          {events.slice(0, 10).map(e => (
            <div key={e.id} className="flex items-center gap-3 px-4 py-1.5 hover:bg-white/[0.02] group">
              <div className="w-1 h-8 bg-cyan-500/40 rounded-full flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-white/75 font-medium truncate">{e.summary}</p>
                <p className="text-[9px] text-white/25 flex items-center gap-1"><Clock className="h-2.5 w-2.5" /> {formatEventTime(e)}</p>
              </div>
              <Button onClick={() => handleDelete(e.id, e.summary)} size="sm" variant="ghost" className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"><Trash2 className="h-3 w-3 text-red-400/60" /></Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
