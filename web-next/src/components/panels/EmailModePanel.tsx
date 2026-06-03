'use client';

import React, { useState, useEffect } from 'react';
import { Mail } from 'lucide-react';
import { EmailItemSkeleton } from '@/components/Skeleton';

/* ── EmailModePanel ──────────────────────────────────────────────────
   Gmail integration with OAuth. Shows mock data if not configured.
   ──────────────────────────────────────────────────────────────────── */

interface Email {
  id: string; from: string; subject: string; preview: string;
  unread: boolean; time: string;
}

const API = '/api/emails';

export default function EmailModePanel() {
  const [emails, setEmails] = useState<Email[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchEmails() {
      try {
        const res = await fetch(API);
        if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      if (!Array.isArray(data)) {
        throw new Error('Invalid response format');
      }
      setEmails(data);
        setError(null);
      } catch (e) {
        setError('Gmail API not configured. Set GMAIL_CREDENTIALS_FILE in .env');
        setEmails([
          { id: '1', from: 'neural-core@jarvis.ai', subject: 'System Sync Complete', preview: 'All neural pathways synchronized.', unread: true, time: '2m' },
          { id: '2', from: 'dev@jarvis.ai', subject: 'Shader Update v8.0', preview: 'Neon contour shader deployed.', unread: true, time: '1h' },
          { id: '3', from: 'alerts@jarvis.ai', subject: 'Bloom Intensity Alert', preview: 'Threshold adjusted to 0.0.', unread: false, time: '3h' },
        ]);
      } finally {
        setLoading(false);
      }
    }
    fetchEmails();
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.06]">
        <span className="text-[9px] tracking-[0.2em] uppercase text-white/30">Inbox</span>
        <span className="text-[9px] text-white/20">{emails.filter(e=> e.unread).length} new</span>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2 scrollbar-hide">
        {loading && (
          <>
            <EmailItemSkeleton />
            <EmailItemSkeleton />
            <EmailItemSkeleton />
          </>
        )}
        {error && (
          <div className="text-center py-6 px-4">
            <Mail className="w-8 h-8 mx-auto text-white/10 mb-3" />
            <p className="text-xs text-white/30 mb-1">Gmail API not configured</p>
            <p className="text-[10px] text-white/20">{error}</p>
          </div>
        )}
        {!loading && !error && emails.map((email) => (
          <div
            key={email.id}
            className={`glass-base rounded-xl p-3 cursor-pointer transition-all ${
              email.unread ? 'border-l-2 border-cyan-400/30' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className={`text-[11px] ${email.unread ? 'text-cyan-300/70 font-medium' : 'text-white/40'}`}>
                {email.from}
              </span>
              <span className="text-[9px] text-white/20">{email.time}</span>
            </div>
            <p className={`text-[12px] mb-1 ${email.unread ? 'text-white/80' : 'text-white/50'}`}>
              {email.subject}
            </p>
            <p className="text-[10px] text-white/30 line-clamp-1">{email.preview}</p>
            {email.unread && <span className="inline-block w-[6px] h-[6px] rounded-full bg-cyan-400 mt-1.5" />}
          </div>
        ))}
      </div>
    </div>
  );
}