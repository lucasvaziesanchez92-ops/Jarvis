'use client';

import { useEffect, useState, useCallback } from 'react';
import { useJarvisStore } from '@/store/jarvisStore';
import { API_BASE } from '@/lib/api';
import { speak as ttsSpeak, stop as ttsStop, onTTSEvent } from '@/lib/tts';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
  attachments?: Array<{key: string, filename: string, size?: number, content_type?: string}>;
  toolCalls?: Array<{
    tool: string;
    input: Record<string, unknown>;
    output?: string;
  }>;
}

interface AppSettings {
  apiUrl: string;
  autoConnect: boolean;
}

function getApiUrl(): string {
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8001'
  }
  return API_BASE
}

function loadSettings(): AppSettings {
  return { apiUrl: getApiUrl(), autoConnect: true };
}

function makeId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
}

/* ── Global WebSocket (true singleton, not tied to component lifecycle) ── */
let globalWs: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectDelay = 1000;
let refCount = 0;
let listeners: Array<{
  onStatus: (s: 'disconnected' | 'connecting' | 'connected' | 'error') => void;
  onBackendStatus: (s: 'disconnected' | 'connecting' | 'connected' | 'error') => void;
}> = [];

function notifyStatus(status: 'disconnected' | 'connecting' | 'connected' | 'error') {
  listeners.forEach(l => l.onStatus(status));
  listeners.forEach(l => l.onBackendStatus(status));
}

function ensureConnection() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }

  // Already connected or connecting — no need to create a new one
  if (globalWs && (globalWs.readyState === WebSocket.OPEN || globalWs.readyState === WebSocket.CONNECTING)) {
    return;
  }

  if (globalWs) {
    globalWs.close();
    globalWs = null;
  }

  const settings = loadSettings();
  const apiUrl = settings.apiUrl;
  const wsProtocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
  const wsHost = apiUrl.replace(/^https?:\/\//, '');
  const wsUrl = `${wsProtocol}://${wsHost}/api/v1/ws/chat`;

  notifyStatus('connecting');

  let ws: WebSocket;
  try {
    ws = new WebSocket(wsUrl);
  } catch (e) {
    notifyStatus('error');
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    globalWs = ws;
    reconnectDelay = 1000;
    notifyStatus('connected');
  };

  ws.onclose = () => {
    globalWs = null;
    
    // Si se cortó la conexión y había un mensaje streameando, lo cerramos limpio.
    const store = useJarvisStore.getState();
    const msgs = store.chatMessages;
    const last = msgs[msgs.length - 1];
    if (last && last.isStreaming) {
      useJarvisStore.setState({ chatMessages: [...msgs.slice(0, -1), { ...last, isStreaming: false }] });
      store.setLastAssistantText(last.content);
      store.setActivityState('idle');
      if (store.voiceEnabled && last.content) {
        ttsSpeak(last.content);
      }
    }

    // Only reconnect if there are still active listeners
    if (refCount <= 0) return;
    notifyStatus('disconnected');
    useJarvisStore.getState().setActivityState('idle');
    scheduleReconnect();
  };

  ws.onerror = () => {
    notifyStatus('error');
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      const store = useJarvisStore.getState();

      if (data.type === 'token' && data.content) {
        useJarvisStore.setState(s => {
          const msgs = s.chatMessages;
          const last = msgs[msgs.length - 1];
          if (last && last.role === 'assistant' && last.isStreaming) {
            // If it's already streaming, ignore the token
            return s;
          }
          // Create a new status message
          const newStatus: ChatMessage = { id: makeId(), role: 'assistant', content: `▸ ${data.content}`, isStreaming: true };
          return { chatMessages: [...msgs, newStatus] };
        });
        useJarvisStore.getState().setActivityState('thinking');
      }

      if (data.type === 'stream' && data.content) {
        useJarvisStore.setState(s => {
          const msgs = s.chatMessages;
          const last = msgs[msgs.length - 1];
          
          if (!last || last.role !== 'assistant' || !last.isStreaming) {
            // Create new message if no streaming assistant message exists
            const newMsg: ChatMessage = { id: makeId(), role: 'assistant', content: data.content, isStreaming: true };
            return { chatMessages: [...msgs, newMsg] };
          }
          
          // If the last message is a status message (▸ Pensando...), replace it entirely
          if (last.content.startsWith('▸ ')) {
            const updated = { ...last, content: data.content };
            return { chatMessages: [...msgs.slice(0, -1), updated] };
          }
          
          // Otherwise, append to existing message
          const updated = { ...last, content: last.content + data.content };
          return { chatMessages: [...msgs.slice(0, -1), updated] };
        });
        const currentStore = useJarvisStore.getState();
        currentStore.setLastAssistantText(currentStore.chatMessages[currentStore.chatMessages.length - 1]?.content || '');
      }

      if (data.type === 'tool_start') {
        store.setActivityState('thinking');
        const msgs = useJarvisStore.getState().chatMessages;
        const last = msgs[msgs.length - 1];
        if (last && last.role === 'assistant') {
          useJarvisStore.setState({
            chatMessages: [...msgs.slice(0, -1), {
              ...last,
              toolCalls: [...(last.toolCalls || []), { tool: data.tool_name, input: data.tool_input }],
            }]
          });
        }
      }

      if (data.type === 'tool_end') {
        const msgs = useJarvisStore.getState().chatMessages;
        const last = msgs[msgs.length - 1];
        if (last && last.role === 'assistant') {
          let updated = false;
          const newToolCalls = last.toolCalls?.map(tc => {
            if (!updated && !tc.output && (!data.tool_name || tc.tool === data.tool_name)) {
              updated = true;
              return { ...tc, output: typeof data.tool_output === 'string' ? data.tool_output : JSON.stringify(data.tool_output) };
            }
            return tc;
          });
          useJarvisStore.setState({
            chatMessages: [...msgs.slice(0, -1), {
              ...last,
              toolCalls: newToolCalls,
            }]
          });
        }
      }

      if (data.type === 'done') {
        const msgs = useJarvisStore.getState().chatMessages;
        const last = msgs[msgs.length - 1];
        if (last && last.isStreaming) {
          useJarvisStore.setState({ chatMessages: [...msgs.slice(0, -1), { ...last, isStreaming: false }] });
          store.setLastAssistantText(last.content);
        }
        store.setActivityState('idle');
        // Auto-TTS when voice is enabled (robust module in lib/tts.ts)
        if (useJarvisStore.getState().voiceEnabled && last) {
          ttsSpeak(last.content);
        }
      }

      if (data.type === 'error') {
        const msgs = useJarvisStore.getState().chatMessages;
        const last = msgs[msgs.length - 1];
        if (last && last.isStreaming) {
          useJarvisStore.setState({
            chatMessages: [...msgs.slice(0, -1), {
              ...last,
              isStreaming: false,
              content: last.content + `\n[Error: ${data.content}]`,
            }]
          });
        }
        store.setActivityState('idle');
      }
    } catch (e) {
      console.error('[WS] Parse error:', e);
    }
  };
}

function scheduleReconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  const delay = reconnectDelay;
  reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
  reconnectTimer = setTimeout(ensureConnection, delay);
}

function teardownConnection() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
  if (globalWs) { globalWs.close(); globalWs = null; }
  listeners = [];
}

export function useJarvisChat() {
  const store = useJarvisStore();
  const [status, setStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [settings] = useState<AppSettings>(loadSettings);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    refCount++;

    const listener = {
      onStatus: setStatus,
      onBackendStatus: (s: 'disconnected' | 'connecting' | 'connected' | 'error') => store.setBackendStatus(s),
    };
    listeners.push(listener);

    // Only create a new connection if we don't have a working one
    if (!globalWs || globalWs.readyState !== WebSocket.OPEN) {
      ensureConnection();
    } else {
      listener.onStatus('connected');
      listener.onBackendStatus('connected');
    }

    // Attempt to sync history when we know the session ID
    if (store.chatSessionId) {
      fetch(`${settings.apiUrl}/api/v1/chat/history/${store.chatSessionId}`)
        .then(res => res.json())
        .then(data => {
          if (data && Array.isArray(data.messages)) {
            // Merge or set messages here. To avoid duplicate IDs, 
            // we overwrite if our current length is less than the backend's.
            if (data.messages.length > store.chatMessages.length) {
               store.setChatMessages(data.messages.map((m: any) => ({
                 id: m.id || makeId(),
                 role: m.role,
                 content: m.content,
                 isStreaming: false,
                 toolCalls: m.tool_calls
               })));
            }
          }
        })
        .catch(err => console.error("Error fetching history:", err));
    }

    return () => {
      refCount--;
      listeners = listeners.filter(l => l !== listener);
    };
  }, [settings.apiUrl, store.chatSessionId]);

  const sendMessage = useCallback((text: string, attachments?: Array<{key: string; filename: string}>) => {
    const msg = text.trim();
    if (!msg && (!attachments || attachments.length === 0)) return;

    store.setLastUserText(msg);
    store.setChatInput('');

    if (!globalWs || globalWs.readyState !== WebSocket.OPEN) {
      store.setActivityState('thinking');
      setTimeout(() => {
        store.appendChatMessage({
          id: makeId(),
          role: 'assistant',
          content: `[Backend offline] I received: "${msg}"\n\nPlease start the backend to get real AI responses.\n\nRun: .\\INICIAR_BACKEND.bat`,
          isStreaming: false,
        });
        store.setActivityState('idle');
      }, 1000);
      return;
    }

    store.setActivityState('thinking');
    globalWs.send(JSON.stringify({
      message: msg,
      session_id: store.chatSessionId,
      persona: store.persona?.name || 'profesional',
      attachments: attachments || [],
      history: store.chatMessages.map(m => ({
        role: m.role,
        content: m.content
      })),
    }));
  }, [store]);

  const retryConnection = useCallback(() => {
    if (globalWs) { globalWs.close(); globalWs = null; }
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    reconnectDelay = 1000;
    ensureConnection();
  }, []);

  const clearChat = useCallback(() => {
    store.clearChat();
  }, [store]);

  return {
    messages: store.chatMessages,
    input: store.chatInput,
    setInput: store.setChatInput,
    status,
    sendMessage,
    retryConnection,
    clearChat,
    isConnected: status === 'connected',
    isConnecting: status === 'connecting',
    hasError: status === 'error',
  };
}

