import type {
  Conversation,
  Memory,
  SystemSettings,
  SystemStatus,
  OllamaHealth,
  Message,
  RetrievedConversation,
  N8nTestResponse,
  GeminiHealth,
} from '../types';

const API_BASE = 'http://127.0.0.1:8000/api';

export const api = {
  // Conversations
  async getConversations(): Promise<Conversation[]> {
    const res = await fetch(`${API_BASE}/conversations`);
    if (!res.ok) throw new Error('Failed to load conversations');
    const data = await res.json();
    return data.conversations;
  },

  async createConversation(title?: string): Promise<Conversation> {
    const res = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: title || 'New Session' }),
    });
    if (!res.ok) throw new Error('Failed to create conversation');
    const data = await res.json();
    return data.conversation;
  },

  async getConversation(id: string): Promise<{ conversation: Conversation; messages: Message[] }> {
    const res = await fetch(`${API_BASE}/conversations/${id}`);
    if (!res.ok) throw new Error('Failed to get conversation');
    return await res.json();
  },

  async deleteConversation(id: string): Promise<boolean> {
    const res = await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' });
    return res.ok;
  },

  async clearAllConversations(): Promise<boolean> {
    const res = await fetch(`${API_BASE}/conversations`, { method: 'DELETE' });
    return res.ok;
  },

  async searchConversations(query: string, limit = 4): Promise<RetrievedConversation[]> {
    const res = await fetch(`${API_BASE}/conversations/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.results || [];
  },

  // Memories
  async getMemories(): Promise<Memory[]> {
    const res = await fetch(`${API_BASE}/memories`);
    if (!res.ok) throw new Error('Failed to load memories');
    const data = await res.json();
    return data.memories;
  },

  async createMemory(content: string, category = 'user_preference'): Promise<Memory> {
    const res = await fetch(`${API_BASE}/memories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, category }),
    });
    if (!res.ok) throw new Error('Failed to save memory');
    const data = await res.json();
    return data.memory;
  },

  async updateMemory(id: string, content: string, category?: string): Promise<boolean> {
    const res = await fetch(`${API_BASE}/memories/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, category }),
    });
    return res.ok;
  },

  async deleteMemory(id: string): Promise<boolean> {
    const res = await fetch(`${API_BASE}/memories/${id}`, { method: 'DELETE' });
    return res.ok;
  },

  async searchMemories(query: string, category?: string): Promise<Memory[]> {
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (category && category !== 'all') params.append('category', category);
    const res = await fetch(`${API_BASE}/memories?${params.toString()}`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.memories || [];
  },

  // Settings & Status
  async getSettings(): Promise<SystemSettings> {
    const res = await fetch(`${API_BASE}/settings`);
    if (!res.ok) throw new Error('Failed to load settings');
    const data = await res.json();
    return data.settings;
  },

  async updateSettings(settings: Partial<SystemSettings>): Promise<SystemSettings> {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    if (!res.ok) throw new Error('Failed to update settings');
    const data = await res.json();
    return data.settings;
  },

  async testN8nWebhook(webhook_url?: string, auth_token?: string, payload?: Record<string, any>): Promise<N8nTestResponse> {
    const res = await fetch(`${API_BASE}/settings/n8n/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ webhook_url, auth_token, payload }),
    });
    return await res.json();
  },

  async getSystemStatus(): Promise<SystemStatus> {
    const res = await fetch(`${API_BASE}/settings/system-status`);
    if (!res.ok) return { message: 'System status unavailable' };
    return await res.json();
  },

  async getOllamaStatus(): Promise<OllamaHealth> {
    try {
      const res = await fetch(`${API_BASE}/settings/ollama-status`);
      if (!res.ok) throw new Error('Ollama status check failed');
      return await res.json();
    } catch {
      return {
        status: 'disconnected',
        connected: false,
        url: 'http://localhost:11434',
        models: [],
        message: 'Could not connect to Ollama backend service.',
      };
    }
  },

  async getOllamaModels(): Promise<string[]> {
    try {
      const res = await fetch(`${API_BASE}/settings/ollama-models`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.models || [];
    } catch {
      return [];
    }
  },

  async getGeminiStatus(): Promise<GeminiHealth> {
    try {
      const res = await fetch(`${API_BASE}/settings/gemini-status`);
      if (!res.ok) throw new Error('Gemini status check failed');
      return await res.json();
    } catch {
      return {
        status: 'disconnected',
        connected: false,
        models: ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash'],
        message: 'Could not connect to Google Gemini endpoint.',
      };
    }
  },

  async getGeminiModels(): Promise<string[]> {
    try {
      const res = await fetch(`${API_BASE}/settings/gemini-models`);
      if (!res.ok) return ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash'];
      const data = await res.json();
      return data.models || ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash'];
    } catch {
      return ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash'];
    }
  },

  async getProviders(): Promise<any> {
    const res = await fetch(`${API_BASE}/settings/providers`);
    if (!res.ok) throw new Error('Failed to load providers');
    return await res.json();
  },

  async listTools(): Promise<{ tools: any[]; allowed_apps: string[]; allowed_folders: string[] }> {
    const res = await fetch(`${API_BASE}/tools`);
    if (!res.ok) throw new Error('Failed to load tools');
    return await res.json();
  },

  async executeTool(name: string, args: Record<string, any> = {}): Promise<any> {
    const res = await fetch(`${API_BASE}/tools/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, arguments: args }),
    });
    if (!res.ok) throw new Error('Tool execution failed');
    return await res.json();
  },

  // Streaming Chat via SSE
  async streamChat(
    conversationId: string,
    message: string,
    model: string,
    callbacks: {
      onChunk: (text: string) => void;
      onThinking?: (text: string) => void;
      onToolStart?: (tools: any[]) => void;
      onExecutingTool?: (tool: string, args: any) => void;
      onToolResult?: (tool: string, result: any) => void;
      onStatus?: (status: string) => void;
      onError: (err: string) => void;
      onDone: () => void;
      onConversationId?: (id: string) => void;
    }
  ) {
    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          message,
          model,
        }),
      });

      if (!response.ok) {
        const errText = await response.text();
        callbacks.onError(`HTTP Error ${response.status}: ${errText}`);
        return;
      }

      const serverConvId = response.headers.get('X-Conversation-Id');
      if (serverConvId && callbacks.onConversationId) {
        callbacks.onConversationId(serverConvId);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks.onError('ReadableStream not supported on response body');
        return;
      }

      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            const rawJson = trimmed.slice(6);
            try {
              const parsed = JSON.parse(rawJson);
              const { type, content, tools, tool, arguments: toolArgs, result } = parsed;

              if (type === 'chunk') callbacks.onChunk(content);
              else if (type === 'thinking') callbacks.onThinking?.(content);
              else if (type === 'tool_call_start') callbacks.onToolStart?.(tools);
              else if (type === 'executing_tool') callbacks.onExecutingTool?.(tool, toolArgs);
              else if (type === 'tool_result') callbacks.onToolResult?.(tool, result);
              else if (type === 'status') callbacks.onStatus?.(content);
              else if (type === 'error') callbacks.onError(content);
              else if (type === 'done') callbacks.onDone();
            } catch {
              // Ignore malformed SSE lines
            }
          }
        }
      }
      callbacks.onDone();
    } catch (e: any) {
      callbacks.onError(e.message || 'Stream connection error');
    }
  },

  // High-Fidelity Local Whisper Audio Transcription
  async transcribeAudio(blob: Blob, filename: string = 'recording.webm'): Promise<string> {
    const formData = new FormData();
    formData.append('file', blob, filename);

    const res = await fetch(`${API_BASE}/voice/transcribe`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      throw new Error(`Whisper transcription failed with status ${res.status}`);
    }

    const data = await res.json();
    return data.text || '';
  },
};
