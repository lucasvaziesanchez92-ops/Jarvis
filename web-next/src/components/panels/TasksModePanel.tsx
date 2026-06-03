'use client';

import React, { useState, useEffect, KeyboardEvent } from 'react';
import { Check, Trash2, Plus } from 'lucide-react';
import { TaskItemSkeleton } from '@/components/Skeleton';

/* ── TasksModePanel ────────────────────────────────────────────────────
   Clean task list with add/toggle/delete and priority dots.
   ───────────────────────────────────────────────────────────────────── */

interface Task {
  id: string;
  text: string;
  completed: boolean;
  priority: 'low' | 'medium' | 'high';
}

const API = '/api';

const PRIORITY_COLORS = {
  low: 'bg-green-400',
  medium: 'bg-amber-400',
  high: 'bg-red-400',
};

export default function TasksModePanel() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTask, setNewTask] = useState('');
  const [priority, setPriority] = useState<Task['priority']>('medium');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTasks = async () => {
    try {
      const res = await fetch(`${API}/todos?show_completed=true`);
      if (!res.ok) throw new Error('Failed to fetch tasks');
      const data = await res.json();
      if (!Array.isArray(data)) {
        throw new Error('Invalid response format');
      }
      setTasks(data);
      setError(null);
    } catch (e) {
      setError('Could not connect to backend');
      setTasks([
        { id: '1', text: 'Review neural interface specs', completed: false, priority: 'high' },
        { id: '2', text: 'Calibrate bloom intensity', completed: true, priority: 'medium' },
        { id: '3', text: 'Sync with backend API', completed: false, priority: 'high' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTasks(); }, []);

  const addTask = () => {
    if (!newTask.trim()) return;
    const t = { id: crypto.randomUUID(), text: newTask, completed: false, priority };
    setTasks(prev => [...prev, t]);
    setNewTask('');
    setPriority('medium');
    fetch(`${API}/todos`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: newTask, priority }),
    }).catch(() => {});
  };

  const toggleTask = (id: string) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, completed: !t.completed } : t));
    fetch(`${API}/todos/${id}/complete`, { method: 'PATCH' }).catch(() => {});
  };

  const deleteTask = (id: string) => {
    setTasks(prev => prev.filter(t => t.id !== id));
    fetch(`${API}/todos/${id}`, { method: 'DELETE' }).catch(() => {});
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') addTask();
  };

  return (
    <div className="flex flex-col h-full">
      {/* Task list */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2 scrollbar-hide">
        {loading && (
          <>
            <TaskItemSkeleton />
            <TaskItemSkeleton />
            <TaskItemSkeleton />
          </>
        )}
        {error && (
          <div className="text-center py-8 text-red-400/60 text-xs">{error}</div>
        )}
        {!loading && !error && tasks.length === 0 && (
          <p className="text-xs text-white/20 text-center mt-8">No tasks yet. Add one below.</p>
        )}

        {tasks.map((task) => (
          <div
            key={task.id}
            className={`flex items-center gap-3 px-3 py-3 glass-base rounded-xl transition-all group ${
              task.completed ? 'opacity-40' : ''
            }`}
          >
            {/* Checkbox */}
            <button
              onClick={() => toggleTask(task.id)}
              className={`shrink-0 w-5 h-5 rounded-md border flex items-center justify-center transition-all ${
                task.completed
                  ? 'bg-cyan-400/20 border-cyan-400/50'
                  : 'border-white/20 hover:border-cyan-400/40'
              }`}
              aria-label={task.completed ? 'Mark incomplete' : 'Mark complete'}
            >
              {task.completed && <Check className="w-3 h-3 text-cyan-400" />}
            </button>

            {/* Text */}
            <span
              className={`flex-1 text-[13px] truncate ${
                task.completed ? 'line-through text-white/30' : 'text-white/80'
              }`}
            >
              {task.text}
            </span>

            {/* Priority dot */}
            <span className={`w-[6px] h-[6px] rounded-full shrink-0 ${PRIORITY_COLORS[task.priority]}`} />

            {/* Delete */}
            <button
              onClick={() => deleteTask(task.id)}
              className="opacity-0 group-hover:opacity-100 p-1 text-white/20 hover:text-red-400 transition-all"
              aria-label="Delete task"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>

      {/* Add task bar */}
      <div className="px-3 py-2 border-t border-white/[0.06] space-y-2">
        {/* Priority selector */}
        <div className="flex gap-2">
          {(['low', 'medium', 'high'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPriority(p)}
              className={`px-2.5 py-1 rounded-full text-[10px] font-medium uppercase tracking-wider transition-all ${
                priority === p
                  ? 'bg-white/10 text-white/80'
                  : 'bg-transparent text-white/20 hover:text-white/40'
              }`}
            >
              <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1 ${PRIORITY_COLORS[p]}`} />
              {p}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <input
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Add neural task..."
            className="flex-1 bg-white/[0.03] border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-[13px] text-white/90 outline-none placeholder:text-white/20 focus:border-cyan-400/30 btn-focus transition-all"
          />
          <button
            onClick={addTask}
            className="flex items-center justify-center w-10 h-10 rounded-xl btn-cyan shrink-0"
            aria-label="Add task"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
