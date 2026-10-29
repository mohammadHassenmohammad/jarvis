import React, { useState, useEffect } from 'react';
import type { SystemSettings, OllamaHealth, GeminiHealth } from '../types';
import { X, Check, RefreshCw, Cpu, Volume2, Mic, Radio, Zap, Link2, Shield, Search, Cloud, Key } from 'lucide-react';
import { api } from '../services/api';
import { speechService, type VoiceOption } from '../services/speech';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: SystemSettings | null;
  ollamaHealth: OllamaHealth | null;
  onSave: (newSettings: Partial<SystemSettings>) => Promise<void>;
  onRefreshHealth: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  settings,
  ollamaHealth,
  onSave,
  onRefreshHealth,
}) => {
  const [model, setModel] = useState('jarvis:latest');
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [memoryEnabled, setMemoryEnabled] = useState(true);
  const [voiceAutoSpeak, setVoiceAutoSpeak] = useState(true);
  const [speechRate, setSpeechRate] = useState('1.0');
  const [speechPitch, setSpeechPitch] = useState('1.0');
  const [voiceInputMode, setVoiceInputMode] = useState<'click' | 'push_to_talk'>('click');
  const [wakeWordEnabled, setWakeWordEnabled] = useState(false);
  const [wakeWord, setWakeWord] = useState('jarvis');
  const [preferredVoice, setPreferredVoice] = useState('');
  const [voiceLanguage, setVoiceLanguage] = useState('en-IN');
  const [vadSilenceTimeout, setVadSilenceTimeout] = useState('1.4');
  const [voiceFeedback, setVoiceFeedback] = useState(true);
  const [maxRecordingDuration, setMaxRecordingDuration] = useState('30');
  const [interruptOnWake, setInterruptOnWake] = useState(true);
  const [continuousMode, setContinuousMode] = useState(true);
  const [whisperBackendEnabled, setWhisperBackendEnabled] = useState(true);
  const [availableVoices, setAvailableVoices] = useState<VoiceOption[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // n8n Webhook Integration State (Optional & Disabled by Default)
  const [n8nEnabled, setN8nEnabled] = useState(false);
  const [n8nWebhookUrl, setN8nWebhookUrl] = useState('');
  const [n8nAuthToken, setN8nAuthToken] = useState('');
  const [n8nHasToken, setN8nHasToken] = useState(false);
  const [n8nTesting, setN8nTesting] = useState(false);
  const [n8nTestStatus, setN8nTestStatus] = useState<{ type: 'success' | 'error' | 'idle'; message: string }>({
    type: 'idle',
    message: '',
  });

  // Conversation Retrieval State
  const [retrievalEnabled, setRetrievalEnabled] = useState(true);
  const [retrievalLimit, setRetrievalLimit] = useState('3');

  // Provider & Gemini Cloud State
  const [provider, setProvider] = useState<'ollama' | 'gemini'>('ollama');
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [geminiHasKey, setGeminiHasKey] = useState(false);
  const [geminiModel, setGeminiModel] = useState('gemini-1.5-flash');
  const [geminiHealth, setGeminiHealth] = useState<GeminiHealth | null>(null);
  const [availableGeminiModels, setAvailableGeminiModels] = useState<string[]>([
    'gemini-1.5-flash',
    'gemini-2.0-flash',
    'gemini-1.5-pro',
    'gemini-2.5-flash',
  ]);

  useEffect(() => {
    if (settings) {
      setModel(settings.model || 'jarvis:latest');
      setSystemPrompt(settings.system_prompt || '');
      setMemoryEnabled(settings.memory_enabled !== 'false');
      setVoiceAutoSpeak(settings.voice_auto_speak !== 'false');
      setSpeechRate(settings.speech_rate || '1.0');
      setSpeechPitch(settings.speech_pitch || '1.0');
      setVoiceInputMode((settings.voice_input_mode as any) || 'click');
      setWakeWordEnabled(settings.wake_word_enabled === 'true');
      setWakeWord(settings.wake_word || 'jarvis');
      setContinuousMode(settings.continuous_mode !== 'false');
      setWhisperBackendEnabled(settings.whisper_backend_enabled !== 'false');
      setPreferredVoice(settings.preferred_voice || '');
      setVoiceLanguage(settings.voice_language || 'en-IN');
      setVadSilenceTimeout(settings.vad_silence_timeout || '1.4');
      setVoiceFeedback(settings.voice_feedback !== 'false');
      setMaxRecordingDuration(settings.max_recording_duration || '30');
      setInterruptOnWake(settings.interrupt_on_wake !== 'false');
      setN8nEnabled(settings.n8n_enabled === 'true');
      setN8nWebhookUrl(settings.n8n_webhook_url || '');
      setN8nAuthToken(settings.n8n_auth_token || '');
      setN8nHasToken(settings.n8n_has_token === 'true');
      setRetrievalEnabled(settings.retrieval_enabled !== 'false');
      setRetrievalLimit(settings.retrieval_limit || '3');
      setProvider((settings.provider as any) === 'gemini' ? 'gemini' : 'ollama');
      setGeminiApiKey(settings.gemini_api_key || '');
      setGeminiHasKey(settings.gemini_has_key === 'true');
      setGeminiModel(settings.gemini_model || 'gemini-1.5-flash');
    }
  }, [settings]);

  useEffect(() => {
    if (isOpen) {
      api.getOllamaModels().then((models) => {
        const fastModels = models.filter((m) => !m.includes('qwen3') && !m.includes('instant'));
        if (fastModels.length > 0) {
          setAvailableModels(fastModels);
          if (!model || model.includes('qwen3')) {
            setModel(fastModels[0]);
          }
        } else {
          setAvailableModels(['jarvis:latest', 'jarvis-fast:latest', 'qwen2.5:1.5b']);
        }
      });

      // Load installed browser speech synthesis voices
      const voices = speechService.getAvailableVoices();
      setAvailableVoices(voices);
      if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = () => {
          setAvailableVoices(speechService.getAvailableVoices());
        };
      }

      // Check Gemini Cloud health and model lists
      api.getGeminiStatus().then((gh) => setGeminiHealth(gh));
      api.getGeminiModels().then((models) => {
        if (models && models.length > 0) setAvailableGeminiModels(models);
      });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave({
        provider,
        model: provider === 'gemini' ? geminiModel : model,
        gemini_model: geminiModel,
        gemini_api_key: geminiApiKey.trim(),
        system_prompt: systemPrompt,
        memory_enabled: memoryEnabled ? 'true' : 'false',
        voice_auto_speak: voiceAutoSpeak ? 'true' : 'false',
        speech_rate: speechRate,
        speech_pitch: speechPitch,
        voice_input_mode: voiceInputMode,
        wake_word_enabled: wakeWordEnabled ? 'true' : 'false',
        wake_word: wakeWord,
        continuous_mode: continuousMode ? 'true' : 'false',
        whisper_backend_enabled: whisperBackendEnabled ? 'true' : 'false',
        preferred_voice: preferredVoice,
        voice_language: voiceLanguage,
        vad_silence_timeout: vadSilenceTimeout,
        voice_feedback: voiceFeedback ? 'true' : 'false',
        max_recording_duration: maxRecordingDuration,
        interrupt_on_wake: interruptOnWake ? 'true' : 'false',
        n8n_enabled: n8nEnabled ? 'true' : 'false',
        n8n_webhook_url: n8nWebhookUrl.trim(),
        n8n_auth_token: n8nAuthToken.trim(),
        retrieval_enabled: retrievalEnabled ? 'true' : 'false',
        retrieval_limit: retrievalLimit,
      });
      setSavedSuccess(true);
      setTimeout(() => {
        setSavedSuccess(false);
        onClose();
      }, 700);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestN8n = async () => {
    setN8nTesting(true);
    setN8nTestStatus({ type: 'idle', message: '' });
    try {
      const res = await api.testN8nWebhook(n8nWebhookUrl.trim(), n8nAuthToken.trim());
      if (res.success) {
        setN8nTestStatus({
          type: 'success',
          message: res.message || 'Webhook triggered successfully (Status 200).',
        });
      } else {
        setN8nTestStatus({
          type: 'error',
          message: res.error || 'Webhook test request failed.',
        });
      }
    } catch (e: any) {
      setN8nTestStatus({
        type: 'error',
        message: e.message || 'Connection error dispatching test webhook.',
      });
    } finally {
      setN8nTesting(false);
    }
  };

  const handleTestVoice = () => {
    speechService.testVoice(preferredVoice, parseFloat(speechRate), parseFloat(speechPitch));
  };

  const sttSupported = speechService.isSpeechRecognitionSupported();
  const ttsSupported = speechService.isSpeechSynthesisSupported();

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(3, 7, 18, 0.82)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
        padding: '16px',
      }}
    >
      <div
        className="cyber-card"
        style={{
          width: '640px',
          maxWidth: '100%',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          background: 'rgba(9, 18, 38, 0.96)',
          border: '1px solid var(--cyan-glow)',
          boxShadow: '0 0 35px rgba(0, 240, 255, 0.3)',
          borderRadius: '8px',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid rgba(0, 240, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu className="w-5 h-5 text-[#00f0ff]" />
            <h2 className="font-hud" style={{ fontSize: '18px', color: '#00f0ff', letterSpacing: '1.5px' }}>
              JARVIS PROTOCOL CONFIGURATION
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body Form */}
        <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Audio Engine & Core Diagnostic Bar */}
          <div
            style={{
              padding: '10px 14px',
              borderRadius: '6px',
              background: 'rgba(0, 240, 255, 0.05)',
              border: '1px solid rgba(0, 240, 255, 0.25)',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '12px',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <span
              style={{
                color: provider === 'ollama' ? (ollamaHealth?.connected ? '#00ffaa' : '#ef4444') : (geminiHealth?.connected ? '#a855f7' : '#eab308'),
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontWeight: 600,
              }}
            >
              {provider === 'ollama' ? (
                <>
                  <Cpu className="w-3.5 h-3.5" /> CORE: OLLAMA [LOCAL]
                </>
              ) : (
                <>
                  <Cloud className="w-3.5 h-3.5" /> CORE: GEMINI [CLOUD AI]
                </>
              )}
            </span>
            <span style={{ color: sttSupported ? '#00ffaa' : '#ef4444', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Mic className="w-3.5 h-3.5" /> STT: {sttSupported ? 'OPERATIONAL' : 'UNAVAILABLE'}
            </span>
            <span style={{ color: ttsSupported ? '#00ffaa' : '#ef4444', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Volume2 className="w-3.5 h-3.5" /> TTS: {ttsSupported ? 'OPERATIONAL' : 'UNAVAILABLE'}
            </span>
            <span style={{ color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Radio className="w-3.5 h-3.5" /> MODE: {voiceInputMode === 'push_to_talk' ? 'PUSH-TO-TALK' : 'CLICK-TO-TALK'}
            </span>
            <span style={{ color: wakeWordEnabled ? '#00ffaa' : '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Zap className="w-3.5 h-3.5" /> WAKE: {wakeWordEnabled ? 'ACTIVE' : 'OFF'}
            </span>
          </div>

          {/* AI Provider Selector */}
          <div
            style={{
              padding: '14px',
              borderRadius: '6px',
              background: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(0, 240, 255, 0.25)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="font-tech" style={{ fontSize: '13px', color: '#00f0ff', letterSpacing: '1px' }}>
                NEURAL CORE PROVIDER:
              </label>
              <span
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  color: provider === 'ollama' ? '#00ffaa' : '#eab308',
                  background: provider === 'ollama' ? 'rgba(0,255,170,0.1)' : 'rgba(234,179,8,0.1)',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  border: `1px solid ${provider === 'ollama' ? '#00ffaa' : '#eab308'}`,
                }}
              >
                {provider === 'ollama' ? '100% LOCAL & FREE' : 'CLOUD API'}
              </span>
            </div>

            {/* Provider Tabs */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setProvider('ollama')}
                style={{
                  padding: '10px',
                  borderRadius: '6px',
                  background: provider === 'ollama' ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                  border: provider === 'ollama' ? '1px solid #00f0ff' : '1px solid rgba(255, 255, 255, 0.1)',
                  color: provider === 'ollama' ? '#00f0ff' : '#94a3b8',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '12px' }}>
                  <Cpu className="w-4 h-4" />
                  <span>OLLAMA (LOCAL GPU)</span>
                </div>
                <div style={{ fontSize: '10px', color: '#64748b' }}>
                  Default · Zero Cost · 100% Offline
                </div>
              </button>

              <button
                type="button"
                onClick={() => setProvider('gemini')}
                style={{
                  padding: '10px',
                  borderRadius: '6px',
                  background: provider === 'gemini' ? 'rgba(168, 85, 247, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                  border: provider === 'gemini' ? '1px solid #a855f7' : '1px solid rgba(255, 255, 255, 0.1)',
                  color: provider === 'gemini' ? '#c084fc' : '#94a3b8',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '12px' }}>
                  <Cloud className="w-4 h-4" />
                  <span>GOOGLE GEMINI (CLOUD)</span>
                </div>
                <div style={{ fontSize: '10px', color: '#64748b' }}>
                  Optional Cloud · High Intelligence
                </div>
              </button>
            </div>

            {/* Provider-Specific Configuration */}
            {provider === 'ollama' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label className="font-tech" style={{ fontSize: '12px', color: '#38bdf8' }}>
                    LOCAL MODEL (OLLAMA):
                  </label>
                  <button
                    type="button"
                    onClick={onRefreshHealth}
                    style={{ background: 'none', border: 'none', color: '#00f0ff', cursor: 'pointer', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <RefreshCw className="w-3 h-3" /> Refresh Models
                  </button>
                </div>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'rgba(0, 0, 0, 0.4)',
                    border: '1px solid var(--cyan-border)',
                    borderRadius: '4px',
                    color: '#00f0ff',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                >
                  {availableModels.map((m) => (
                    <option key={m} value={m} style={{ background: '#091226', color: '#fff' }}>
                      {m}
                    </option>
                  ))}
                </select>
                <div style={{ fontSize: '11px', color: '#00ffaa', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Check className="w-3 h-3" /> Runs 100% locally on your RTX GPU. No cloud charges.
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '4px' }}>
                {/* Cloud Cost Protection Alert */}
                <div
                  style={{
                    padding: '8px 12px',
                    borderRadius: '4px',
                    background: 'rgba(234, 179, 8, 0.08)',
                    border: '1px solid rgba(234, 179, 8, 0.35)',
                    fontSize: '11px',
                    color: '#fef08a',
                    lineHeight: '1.4',
                  }}
                >
                  <strong style={{ color: '#eab308' }}>⚠️ Cloud AI Cost Safeguard:</strong> Google Gemini routes queries through Google Cloud. Never silently incurs charges: requests require a valid GEMINI_API_KEY. Default provider is local Ollama.
                </div>

                {/* Gemini Model Selector */}
                <div>
                  <label className="font-tech" style={{ fontSize: '12px', color: '#c084fc', marginBottom: '4px', display: 'block' }}>
                    GEMINI MODEL:
                  </label>
                  <select
                    value={geminiModel}
                    onChange={(e) => setGeminiModel(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      background: 'rgba(0, 0, 0, 0.4)',
                      border: '1px solid rgba(168, 85, 247, 0.5)',
                      borderRadius: '4px',
                      color: '#c084fc',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '13px',
                      outline: 'none',
                    }}
                  >
                    {availableGeminiModels.map((m) => (
                      <option key={m} value={m} style={{ background: '#091226', color: '#fff' }}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Gemini API Key */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <label className="font-tech" style={{ fontSize: '12px', color: '#c084fc', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Key className="w-3.5 h-3.5" /> GEMINI_API_KEY (ENVIRONMENT / SECURE):
                    </label>
                    <span style={{ fontSize: '10px', color: geminiHasKey ? '#00ffaa' : '#64748b', fontFamily: 'var(--font-mono)' }}>
                      {geminiHasKey ? '● KEY CONFIGURED' : '○ NO KEY DETECTED'}
                    </span>
                  </div>
                  <input
                    type="password"
                    value={geminiApiKey}
                    onChange={(e) => setGeminiApiKey(e.target.value)}
                    placeholder={geminiHasKey ? '•••••••• (Configured in .env or backend)' : 'Enter or paste AI Studio Gemini API key...'}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      background: 'rgba(0, 0, 0, 0.5)',
                      border: '1px solid rgba(168, 85, 247, 0.4)',
                      borderRadius: '4px',
                      color: '#f8fafc',
                      fontSize: '13px',
                      fontFamily: 'var(--font-mono)',
                      outline: 'none',
                    }}
                  />
                  <div style={{ fontSize: '10px', color: '#64748b', marginTop: '3px' }}>
                    Priority: reads GEMINI_API_KEY from .env first. Stored only in backend, masked in browser.
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* System Prompt */}
          <div>
            <label className="font-tech" style={{ display: 'block', fontSize: '13px', color: '#38bdf8', marginBottom: '6px' }}>
              JARVIS PERSONA & SYSTEM DIRECTIVE:
            </label>
            <textarea
              rows={3}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--cyan-border)',
                borderRadius: '4px',
                color: '#e2e8f0',
                fontFamily: 'var(--font-body)',
                fontSize: '13px',
                outline: 'none',
                resize: 'vertical',
              }}
            />
          </div>

          {/* Voice Input Mode: Click vs Push-to-Talk */}
          <div style={{ padding: '10px 0', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="font-hud" style={{ fontSize: '14px', color: '#f8fafc', marginBottom: '4px' }}>
              Voice Input Protocol
            </div>
            <div style={{ display: 'flex', gap: '12px', marginTop: '6px' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 12px',
                  background: voiceInputMode === 'click' ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255,255,255,0.03)',
                  border: voiceInputMode === 'click' ? '1px solid #00f0ff' : '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontFamily: 'var(--font-mono)',
                  color: voiceInputMode === 'click' ? '#00f0ff' : '#94a3b8',
                }}
              >
                <input
                  type="radio"
                  name="voiceMode"
                  value="click"
                  checked={voiceInputMode === 'click'}
                  onChange={() => setVoiceInputMode('click')}
                  style={{ accentColor: '#00f0ff' }}
                />
                Click-to-Speak (Toggle Mic)
              </label>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 12px',
                  background: voiceInputMode === 'push_to_talk' ? 'rgba(255, 183, 3, 0.15)' : 'rgba(255,255,255,0.03)',
                  border: voiceInputMode === 'push_to_talk' ? '1px solid #ffb703' : '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontFamily: 'var(--font-mono)',
                  color: voiceInputMode === 'push_to_talk' ? '#ffb703' : '#94a3b8',
                }}
              >
                <input
                  type="radio"
                  name="voiceMode"
                  value="push_to_talk"
                  checked={voiceInputMode === 'push_to_talk'}
                  onChange={() => setVoiceInputMode('push_to_talk')}
                  style={{ accentColor: '#ffb703' }}
                />
                Push-to-Talk (Hold Space or Mic)
              </label>
            </div>
          </div>

          {/* Wake-Word Continuous Detection */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <div>
              <div className="font-hud" style={{ fontSize: '14px', color: '#f8fafc' }}>
                Continuous Wake-Word Detection ("Hey Jarvis")
              </div>
              <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                Monitors audio for "Hey Jarvis" or "Jarvis" and executes command automatically
              </div>
            </div>
            <input
              type="checkbox"
              checked={wakeWordEnabled}
              onChange={(e) => setWakeWordEnabled(e.target.checked)}
              style={{ width: '18px', height: '18px', accentColor: '#00f0ff', cursor: 'pointer' }}
            />
          </div>

          {/* Speech Recognition Language / Accent Selection */}
          <div style={{ padding: '10px 0', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="font-tech" style={{ fontSize: '13px', color: '#38bdf8', marginBottom: '6px' }}>
              SPEECH RECOGNITION ACOUSTIC MODEL / ACCENT:
            </div>
            <select
              value={voiceLanguage}
              onChange={(e) => setVoiceLanguage(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--cyan-border)',
                borderRadius: '4px',
                color: '#00f0ff',
                fontFamily: 'var(--font-mono)',
                fontSize: '13px',
                outline: 'none',
              }}
            >
              <option value="en-IN" style={{ background: '#091226', color: '#fff' }}>
                English (India) [en-IN] - Optimal for Indian English / Accents
              </option>
              <option value="en-US" style={{ background: '#091226', color: '#fff' }}>
                English (United States) [en-US]
              </option>
              <option value="en-GB" style={{ background: '#091226', color: '#fff' }}>
                English (United Kingdom) [en-GB]
              </option>
              <option value="auto" style={{ background: '#091226', color: '#fff' }}>
                System Default / Auto Detect
              </option>
            </select>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Selects the phonetic acoustic model to flawlessly recognize your natural accent and words.
            </div>
          </div>

          {/* Voice Output Selection & Preview */}
          <div style={{ padding: '10px 0', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <div className="font-tech" style={{ fontSize: '13px', color: '#38bdf8' }}>
                JARVIS SYNTHESIS VOICE:
              </div>
              <button
                type="button"
                onClick={handleTestVoice}
                style={{
                  background: 'rgba(0, 240, 255, 0.1)',
                  border: '1px solid #00f0ff',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  color: '#00f0ff',
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <Volume2 className="w-3 h-3" /> Test Voice
              </button>
            </div>
            <select
              value={preferredVoice}
              onChange={(e) => setPreferredVoice(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--cyan-border)',
                borderRadius: '4px',
                color: '#e2e8f0',
                fontFamily: 'var(--font-mono)',
                fontSize: '13px',
                outline: 'none',
              }}
            >
              <option value="">Default (British Jarvis Priority)</option>
              {availableVoices.map((v) => (
                <option key={v.name} value={v.name} style={{ background: '#091226', color: '#fff' }}>
                  {v.name} ({v.lang})
                </option>
              ))}
            </select>
          </div>

          {/* Speech Rate & Pitch Sliders */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <div className="font-tech" style={{ fontSize: '12px', color: '#38bdf8', marginBottom: '4px' }}>
                SPEECH RATE ({speechRate}x):
              </div>
              <input
                type="range"
                min="0.7"
                max="1.5"
                step="0.05"
                value={speechRate}
                onChange={(e) => setSpeechRate(e.target.value)}
                style={{ width: '100%', accentColor: '#00f0ff' }}
              />
            </div>
            <div>
              <div className="font-tech" style={{ fontSize: '12px', color: '#38bdf8', marginBottom: '4px' }}>
                SPEECH PITCH ({speechPitch}x):
              </div>
              <input
                type="range"
                min="0.6"
                max="1.4"
                step="0.05"
                value={speechPitch}
                onChange={(e) => setSpeechPitch(e.target.value)}
                style={{ width: '100%', accentColor: '#00f0ff' }}
              />
            </div>
          </div>

          {/* VAD & Natural Speech Turn-Taking Controls */}
          <div style={{ padding: '10px 0', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <div className="font-tech" style={{ fontSize: '12px', color: '#38bdf8', marginBottom: '4px' }}>
                  END-OF-SPEECH SILENCE ({vadSilenceTimeout}s):
                </div>
                <input
                  type="range"
                  min="0.8"
                  max="2.5"
                  step="0.1"
                  value={vadSilenceTimeout}
                  onChange={(e) => setVadSilenceTimeout(e.target.value)}
                  style={{ width: '100%', accentColor: '#00f0ff' }}
                />
                <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                  Pause allowed before auto-sending (prevents cutoffs)
                </div>
              </div>
              <div>
                <div className="font-tech" style={{ fontSize: '12px', color: '#38bdf8', marginBottom: '4px' }}>
                  MAX DIRECTIVE DURATION ({maxRecordingDuration}s):
                </div>
                <input
                  type="range"
                  min="10"
                  max="60"
                  step="5"
                  value={maxRecordingDuration}
                  onChange={(e) => setMaxRecordingDuration(e.target.value)}
                  style={{ width: '100%', accentColor: '#00f0ff' }}
                />
                <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                  Upper limit for a single spoken voice command
                </div>
              </div>
            </div>
          </div>

          {/* Voice Acknowledgment & Interruption Checkboxes */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="font-hud" style={{ fontSize: '13px', color: '#f8fafc' }}>
                  Acoustic Feedback & Chimes
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                  Play activation sound and "Yes, Sir?" acknowledgment
                </div>
              </div>
              <input
                type="checkbox"
                checked={voiceFeedback}
                onChange={(e) => setVoiceFeedback(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: '#00f0ff', cursor: 'pointer' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="font-hud" style={{ fontSize: '13px', color: '#00ffaa' }}>
                  Continuous ChatGPT Voice Mode
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                  Say "Hey Jarvis" once to start. Listens after each answer without repeating "Hey Jarvis" until you say "Goodbye" or click stop.
                </div>
              </div>
              <input
                type="checkbox"
                checked={continuousMode}
                onChange={(e) => setContinuousMode(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: '#00ffaa', cursor: 'pointer' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="font-hud" style={{ fontSize: '13px', color: '#38bdf8' }}>
                  Whisper Neural Audio Engine
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                  Runs local Whisper model for high-accuracy phonetic grasping and zero transcription errors
                </div>
              </div>
              <input
                type="checkbox"
                checked={whisperBackendEnabled}
                onChange={(e) => setWhisperBackendEnabled(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: '#38bdf8', cursor: 'pointer' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="font-hud" style={{ fontSize: '13px', color: '#f8fafc' }}>
                  Barge-In / Voice Interruption
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                  Halt vocalization when saying "Hey Jarvis" or "Stop" while speaking
                </div>
              </div>
              <input
                type="checkbox"
                checked={interruptOnWake}
                onChange={(e) => setInterruptOnWake(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: '#00f0ff', cursor: 'pointer' }}
              />
            </div>
          </div>

          {/* Memory & Auto-Speak Checkboxes */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="font-hud" style={{ fontSize: '13px', color: '#f8fafc' }}>
                  Auto-Vocalize Responses
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                  Speak answers aloud automatically via local TTS
                </div>
              </div>
              <input
                type="checkbox"
                checked={voiceAutoSpeak}
                onChange={(e) => setVoiceAutoSpeak(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: '#00f0ff', cursor: 'pointer' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="font-hud" style={{ fontSize: '13px', color: '#f8fafc' }}>
                  Long-Term Memory Injection
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                  Recall user preferences and facts across sessions
                </div>
              </div>
              <input
                type="checkbox"
                checked={memoryEnabled}
                onChange={(e) => setMemoryEnabled(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: '#00f0ff', cursor: 'pointer' }}
              />
            </div>

            {/* Relevant Conversation Retrieval (Local-First) */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingTop: '8px',
                borderTop: '1px solid rgba(255,255,255,0.04)',
              }}
            >
              <div>
                <div className="font-hud" style={{ fontSize: '13px', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Search className="w-3.5 h-3.5 text-[#00f0ff]" /> Relevant Conversation Retrieval
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                  Index and recall relevant dialogue from past sessions using local SQLite scoring
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {retrievalEnabled && (
                  <select
                    value={retrievalLimit}
                    onChange={(e) => setRetrievalLimit(e.target.value)}
                    style={{
                      padding: '3px 6px',
                      background: 'rgba(0,0,0,0.4)',
                      border: '1px solid var(--cyan-border)',
                      borderRadius: '4px',
                      color: '#00f0ff',
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                    }}
                    title="Max retrieved excerpts per query"
                  >
                    <option value="2">2 items</option>
                    <option value="3">3 items</option>
                    <option value="4">4 items</option>
                    <option value="5">5 items</option>
                  </select>
                )}
                <input
                  type="checkbox"
                  checked={retrievalEnabled}
                  onChange={(e) => setRetrievalEnabled(e.target.checked)}
                  style={{ width: '16px', height: '16px', accentColor: '#00f0ff', cursor: 'pointer' }}
                />
              </div>
            </div>
          </div>

          {/* Optional Self-Hosted n8n Automation Webhook Card */}
          <div
            style={{
              padding: '14px',
              borderRadius: '6px',
              background: 'rgba(0, 0, 0, 0.35)',
              border: n8nEnabled ? '1px solid rgba(0, 240, 255, 0.4)' : '1px solid rgba(255, 255, 255, 0.1)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Link2 className="w-4 h-4 text-[#00f0ff]" />
                <div>
                  <div className="font-hud" style={{ fontSize: '13px', color: '#00f0ff', letterSpacing: '1px' }}>
                    SELF-HOSTED n8n AUTOMATION (OPTIONAL)
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                    Connect to your private local or self-hosted n8n workflows
                  </div>
                </div>
              </div>
              <input
                type="checkbox"
                checked={n8nEnabled}
                onChange={(e) => setN8nEnabled(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: '#00f0ff', cursor: 'pointer' }}
              />
            </div>

            {n8nEnabled && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '4px' }}>
                <div>
                  <div className="font-tech" style={{ fontSize: '11px', color: '#38bdf8', marginBottom: '4px' }}>
                    WEBHOOK ENDPOINT URL (http:// or https://):
                  </div>
                  <input
                    type="text"
                    value={n8nWebhookUrl}
                    onChange={(e) => setN8nWebhookUrl(e.target.value)}
                    placeholder="e.g., http://localhost:5678/webhook/jarvis-command"
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      background: 'rgba(0, 0, 0, 0.5)',
                      border: '1px solid var(--cyan-border)',
                      borderRadius: '4px',
                      color: '#f8fafc',
                      fontSize: '12px',
                      fontFamily: 'var(--font-mono)',
                      outline: 'none',
                    }}
                  />
                  <div style={{ fontSize: '10px', color: '#64748b', marginTop: '3px' }}>
                    Strict validation: only http/https allowed. Cloud metadata SSRF targets are automatically blocked.
                  </div>
                </div>

                <div>
                  <div className="font-tech" style={{ fontSize: '11px', color: '#38bdf8', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Shield className="w-3 h-3 text-[#00ffaa]" /> AUTH TOKEN / SECRET HEADER (SECURE):
                  </div>
                  <input
                    type="password"
                    value={n8nAuthToken}
                    onChange={(e) => setN8nAuthToken(e.target.value)}
                    placeholder={n8nHasToken ? '•••••••• (Stored securely in backend)' : 'Optional Bearer token or secret...'}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      background: 'rgba(0, 0, 0, 0.5)',
                      border: '1px solid var(--cyan-border)',
                      borderRadius: '4px',
                      color: '#f8fafc',
                      fontSize: '12px',
                      fontFamily: 'var(--font-mono)',
                      outline: 'none',
                    }}
                  />
                  <div style={{ fontSize: '10px', color: '#64748b', marginTop: '3px' }}>
                    Stored strictly in backend SQLite. Never exported to frontend or exposed in logs.
                  </div>
                </div>

                {/* Test Connection Button & Status */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginTop: '4px' }}>
                  <button
                    type="button"
                    onClick={handleTestN8n}
                    disabled={n8nTesting || !n8nWebhookUrl.trim()}
                    className="cyber-button"
                    style={{ padding: '5px 12px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <Zap className="w-3.5 h-3.5" />
                    <span>{n8nTesting ? 'Testing Webhook...' : 'Test Webhook Connection'}</span>
                  </button>

                  {n8nTestStatus.message && (
                    <div
                      style={{
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        background: n8nTestStatus.type === 'success' ? 'rgba(0, 255, 170, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                        border: n8nTestStatus.type === 'success' ? '1px solid #00ffaa' : '1px solid #ef4444',
                        color: n8nTestStatus.type === 'success' ? '#00ffaa' : '#ef4444',
                        maxWidth: '320px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                      title={n8nTestStatus.message}
                    >
                      {n8nTestStatus.message}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '14px 20px',
            borderTop: '1px solid rgba(0, 240, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          {savedSuccess ? (
            <span style={{ color: '#00ffaa', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px' }}>
              <Check className="w-4 h-4" /> Changes Applied Successfully
            </span>
          ) : (
            <div />
          )}

          <div style={{ display: 'flex', gap: '10px' }}>
            <button onClick={onClose} className="cyber-button danger" style={{ padding: '8px 16px' }}>
              Cancel
            </button>
            <button onClick={handleSave} disabled={isSaving} className="cyber-button" style={{ padding: '8px 20px' }}>
              {isSaving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
