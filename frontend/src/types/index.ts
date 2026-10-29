export type AssistantState =
  | 'idle'
  | 'wake_word_monitoring'
  | 'wake_word_detected'
  | 'listening'
  | 'processing_audio'
  | 'transcribing'
  | 'thinking'
  | 'speaking'
  | 'interrupted'
  | 'executing_tool'
  | 'error';

export interface ToolCall {
  id?: string;
  function: {
    name: string;
    arguments: Record<string, any> | string;
  };
}

export interface ToolResult {
  id?: string;
  tool: string;
  result: {
    success: boolean;
    message?: string;
    error?: string;
    [key: string]: any;
  };
}

export interface Message {
  id: string;
  conversation_id?: string;
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  thinking?: string;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
  created_at?: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Memory {
  id: string;
  category: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface SystemSettings {
  model: string;
  provider: string;
  system_prompt: string;
  memory_enabled: string;
  voice_auto_speak: string;
  speech_rate: string;
  speech_pitch: string;
  voice_input_mode?: 'click' | 'push_to_talk';
  wake_word_enabled?: string;
  wake_word?: string;
  preferred_voice?: string;
  voice_language?: string;
  vad_silence_timeout?: string;
  voice_feedback?: string;
  max_recording_duration?: string;
  interrupt_on_wake?: string;
  continuous_mode?: string;
  whisper_backend_enabled?: string;
  n8n_enabled?: string;
  n8n_webhook_url?: string;
  n8n_auth_token?: string;
  n8n_has_token?: string;
  retrieval_enabled?: string;
  retrieval_limit?: string;
  gemini_api_key?: string;
  gemini_has_key?: string;
  gemini_model?: string;
}

export interface GeminiHealth {
  status: 'connected' | 'disconnected' | 'unconfigured' | 'error';
  connected: boolean;
  models: string[];
  message: string;
}

export interface RetrievedConversation {
  conversation_id: string;
  title: string;
  date: string;
  score: number;
  snippet: string;
}

export interface N8nTestResponse {
  success: boolean;
  status_code?: number;
  message?: string;
  error?: string;
  disabled?: boolean;
  response?: any;
}

export interface SystemStatus {
  os?: string;
  hostname?: string;
  cpu_usage_percent?: number;
  ram_total_gb?: number;
  ram_used_gb?: number;
  ram_percent?: number;
  disk_free_gb?: number;
  message?: string;
}

export interface OllamaHealth {
  status: 'connected' | 'disconnected' | 'error';
  connected: boolean;
  url: string;
  models: string[];
  message: string;
}
