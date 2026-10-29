import React, { useState, useEffect, useRef } from 'react';
import type { Conversation, Message, AssistantState, SystemSettings, SystemStatus, OllamaHealth } from './types';
import { api } from './services/api';
import { speechService } from './services/speech';
import { Sidebar } from './components/Sidebar';
import { ArcReactor } from './components/ArcReactor';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { QuickTools } from './components/QuickTools';
import { SettingsModal } from './components/SettingsModal';
import { MemoryManager } from './components/MemoryManager';
import { Clock, Wifi, WifiOff, Menu, Cpu, CheckCircle, Cloud, Mic } from 'lucide-react';

export const App: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const activeConversationIdRef = useRef<string | null>(null);
  const handleSendMessageRef = useRef<(text: string) => Promise<void>>(() => Promise.resolve());

  const updateActiveConversationId = (id: string | null) => {
    activeConversationIdRef.current = id;
    setActiveConversationId(id);
    if (id) {
      try {
        localStorage.setItem('jarvis_active_session_id', id);
      } catch {}
    } else {
      try {
        localStorage.removeItem('jarvis_active_session_id');
      } catch {}
    }
  };

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [assistantState, setAssistantState] = useState<AssistantState>('idle');
  const [currentToolName, setCurrentToolName] = useState<string>('');

  // Voice States
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speechTranscript, setSpeechTranscript] = useState('');
  const [isMuted, setIsMuted] = useState(false);
  const [voiceInputMode, setVoiceInputMode] = useState<'click' | 'push_to_talk'>('click');
  const [audioLevel, setAudioLevel] = useState(0);
  const [wakeWordActive, setWakeWordActive] = useState(false);
  const [isContinuousVoiceActive, setIsContinuousVoiceActive] = useState(false);
  const [micPermissionNeeded, setMicPermissionNeeded] = useState(false);

  // System & Telemetry States
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [ollamaHealth, setOllamaHealth] = useState<OllamaHealth | null>(null);
  const [currentTimeStr, setCurrentTimeStr] = useState('');
  const [modelToast, setModelToast] = useState<string | null>(null);

  // UI Modal States
  const [isSettingsOpen, setIsSettingsOpen] = useState(() => typeof window !== 'undefined' && window.location.search.includes('settings'));
  const [isMemoriesOpen, setIsMemoriesOpen] = useState(() => typeof window !== 'undefined' && window.location.search.includes('memories'));
  const [showSidebar, setShowSidebar] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize clock
  useEffect(() => {
    const updateTime = () => {
      const d = new Date();
      setCurrentTimeStr(d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // Initialize backend data & audio sensors
  useEffect(() => {
    loadInitialData();
    const interval = setInterval(refreshTelemetry, 8000);

    // Immediate check: if mic permission is already granted, activate recognition right away
    speechService.ensureMicrophoneAccess().then((ok) => {
      if (ok) {
        setMicPermissionNeeded(false);
        speechService.safeStartRecognition();
      }
    });

    const handleFirstInteraction = () => {
      speechService.ensureMicrophoneAccess().then((ok) => {
        if (ok) {
          setMicPermissionNeeded(false);
          speechService.safeStartRecognition();
        }
      });
      window.removeEventListener('pointerdown', handleFirstInteraction);
    };
    window.addEventListener('pointerdown', handleFirstInteraction);

    return () => {
      clearInterval(interval);
      window.removeEventListener('pointerdown', handleFirstInteraction);
    };
  }, []);

  const activateMicrophone = async () => {
    const granted = await speechService.ensureMicrophoneAccess();
    if (granted) {
      setMicPermissionNeeded(false);
      speechService.safeStartRecognition();
      setModelToast('AUDIO SENSORS ONLINE // LISTENING FOR "HEY JARVIS"');
      setTimeout(() => setModelToast(null), 3000);
    } else {
      setMicPermissionNeeded(true);
    }
  };

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, assistantState]);

  const loadInitialData = async () => {
    try {
      const s = await api.getSettings();
      setSettings(s);
      if (s?.voice_input_mode) {
        setVoiceInputMode(s.voice_input_mode as any);
      }
      if (s?.wake_word_enabled) {
        setWakeWordActive(s.wake_word_enabled === 'true');
      }
      refreshTelemetry();
      const convs = await api.getConversations();
      setConversations(convs);

      let savedSessionId: string | null = null;
      try {
        savedSessionId = localStorage.getItem('jarvis_active_session_id');
      } catch {}

      const matchedConv = savedSessionId ? convs.find((c) => c.id === savedSessionId) : null;
      if (matchedConv) {
        selectConversation(matchedConv.id);
      } else if (convs.length > 0) {
        selectConversation(convs[0].id);
      } else {
        startNewConversation();
      }
    } catch (e) {
      console.error('Initialization error:', e);
    }
  };

  const refreshTelemetry = async () => {
    try {
      const [health, status] = await Promise.all([
        api.getOllamaStatus(),
        api.getSystemStatus(),
      ]);
      setOllamaHealth(health);
      setSystemStatus(status);
    } catch {}
  };

  const selectConversation = async (id: string) => {
    updateActiveConversationId(id);
    try {
      const data = await api.getConversation(id);
      setMessages(data.messages || []);
    } catch (e) {
      console.error('Failed to load conversation:', e);
    }
  };

  const startNewConversation = async () => {
    try {
      const newConv = await api.createConversation('New Protocol Session');
      updateActiveConversationId(newConv.id);
      setConversations((prev) => [newConv, ...prev.filter((c) => c.id !== newConv.id)]);
      setMessages([]);
    } catch (e) {
      console.error('Failed to create new conversation:', e);
    }
  };

  const deleteConversation = async (id: string) => {
    try {
      await api.deleteConversation(id);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
      if (activeConversationIdRef.current === id) {
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          startNewConversation();
        }
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e);
    }
  };

  const clearAllConversations = async () => {
    if (!window.confirm('Sir, are you certain you wish to purge all conversation logs?')) return;
    try {
      await api.clearAllConversations();
      setConversations([]);
      setMessages([]);
      startNewConversation();
    } catch (e) {
      console.error('Failed to clear conversations:', e);
    }
  };

  // Chat Execution Flow
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    let targetConvId = activeConversationIdRef.current;
    if (!targetConvId) {
      try {
        const newConv = await api.createConversation(text.slice(0, 30));
        targetConvId = newConv.id;
        updateActiveConversationId(targetConvId);
        setConversations((prev) => [newConv, ...prev.filter((c) => c.id !== newConv.id)]);
      } catch (e) {
        console.error('Failed to create session for prompt:', e);
        return;
      }
    }

    const userMsg: Message = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };

    // Lock microphone immediately while waiting for reasoning, tool execution, and speech output
    speechService.lockMicrophone('User message dispatched; awaiting assistant response');
    setSpeechTranscript('');
    setIsListening(false);

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setAssistantState('thinking');

    const assistantMsgId = `asst-${Date.now()}`;
    let accumulatedContent = '';
    let accumulatedThinking = '';

    setMessages((prev) => [
      ...prev,
      {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      },
    ]);

    const activeModel = currentActiveModel;

    await api.streamChat(targetConvId, text, activeModel, {
      onConversationId: (returnedId) => {
        if (returnedId && activeConversationIdRef.current !== returnedId) {
          updateActiveConversationId(returnedId);
        }
      },
      onStatus: (status) => {
        if (status === 'thinking') setAssistantState('thinking');
        else if (status === 'speaking') setAssistantState('speaking');
      },
      onThinking: (thinkChunk) => {
        accumulatedThinking += thinkChunk;
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, thinking: accumulatedThinking } : m))
        );
      },
      onToolStart: (tools) => {
        setAssistantState('executing_tool');
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, tool_calls: tools } : m))
        );
      },
      onExecutingTool: (toolName) => {
        setAssistantState('executing_tool');
        setCurrentToolName(toolName);
      },
      onToolResult: (toolName, result) => {
        // Trigger browser tab open immediately if open_website was executed
        if (toolName === 'open_website') {
          const targetUrl = result?.url || (typeof result === 'string' ? result : '');
          if (targetUrl && (targetUrl.startsWith('http://') || targetUrl.startsWith('https://'))) {
            try {
              window.open(targetUrl, '_blank', 'noopener,noreferrer');
            } catch (e) {
              console.warn('Frontend window.open notice:', e);
            }
          }
        }
        const toolMsg: Message = {
          id: `tool-${Date.now()}`,
          role: 'tool',
          content: result.message || (result.error ? `System Error: ${result.error}` : JSON.stringify(result)),
          tool_results: [{ tool: toolName, result }],
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, toolMsg]);
      },
      onChunk: (chunk) => {
        accumulatedContent += chunk;
        setAssistantState('thinking');
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, content: accumulatedContent } : m))
        );
      },
      onError: (err) => {
        speechService.unlockMicrophone();
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: `[SYSTEM ERROR]: ${err}` }
              : m
          )
        );
        setIsLoading(false);
        setAssistantState('error');
        setTimeout(() => {
          setAssistantState(wakeWordActive ? 'wake_word_monitoring' : 'idle');
          if (wakeWordActive) {
            speechService.safeStartRecognition();
          }
        }, 3000);
      },
      onDone: () => {
        setIsLoading(false);
        setCurrentToolName('');
        setIsListening(false);

        const autoSpeak = settings?.voice_auto_speak !== 'false';
        if (autoSpeak && accumulatedContent && !isMuted) {
          setIsSpeaking(true);
          setIsListening(false);
          setAssistantState('speaking');
          speechService.speak(accumulatedContent, {
            rate: parseFloat(settings?.speech_rate || '1.05'),
            pitch: parseFloat(settings?.speech_pitch || '0.95'),
            preferredVoice: settings?.preferred_voice,
            onStart: () => {
              setIsSpeaking(true);
              setIsListening(false);
              setAssistantState('speaking');
            },
            onEnd: () => {
              setIsSpeaking(false);
              setSpeechTranscript('');
              // Always resume listening immediately once speech and acoustic dissipation are complete
              setIsListening(true);
              setAssistantState('listening');
            },
            onError: (err) => {
              console.warn('TTS playback notice:', err);
              setIsSpeaking(false);
              setSpeechTranscript('');
              setIsListening(true);
              setAssistantState('listening');
            },
          });
        } else {
          speechService.unlockMicrophone();
          setSpeechTranscript('');
          if (speechService.isContinuousSession()) {
            setIsListening(true);
            setAssistantState('listening');
          } else {
            const wakeOn = settings?.wake_word_enabled !== 'false';
            setAssistantState(wakeOn ? 'wake_word_monitoring' : 'idle');
            if (wakeOn) {
              speechService.safeStartRecognition();
            }
          }
        }

        api.getConversations().then(setConversations).catch(() => {});
      },
    });
  };

  useEffect(() => {
    handleSendMessageRef.current = handleSendMessage;
  });

  // Continuous Wake-Word Detection & Live Grasping Lifecycle
  useEffect(() => {
    const isEnabled = settings?.wake_word_enabled !== 'false';
    const isContinuousEnabled = settings?.continuous_mode !== 'false';
    setWakeWordActive(isEnabled);

    speechService.setLanguage(settings?.voice_language || 'en-IN');
    speechService.setVadSilenceTimeout(parseFloat(settings?.vad_silence_timeout || '1.4'));
    speechService.setVoiceFeedback(settings?.voice_feedback !== 'false');
    speechService.setInterruptOnWake(settings?.interrupt_on_wake !== 'false');
    speechService.setMaxRecordingDuration(parseFloat(settings?.max_recording_duration || '30'));
    speechService.setWhisperBackendEnabled(settings?.whisper_backend_enabled !== 'false');

    speechService.setOnContinuousSessionChange((active) => {
      setIsContinuousVoiceActive(active);
    });

    speechService.setOnVocalizingChange((speaking) => {
      setIsSpeaking(speaking);
      if (speaking) {
        setIsListening(false);
        setAssistantState('speaking');
      } else {
        if (speechService.isContinuousSession()) {
          setIsListening(true);
          setAssistantState('listening');
        } else {
          setAssistantState(isEnabled ? 'wake_word_monitoring' : 'idle');
        }
      }
    });

    speechService.setOnContinuousTurnReady(() => {
      if (!speechService.isSpeakingNow()) {
        setIsListening(true);
        setAssistantState('listening');
        setSpeechTranscript('');
      }
    });

    speechService.setOnInterrupt(() => {
      console.log('[VOICE_STATE_MACHINE] TRANSITION: SPEAKING -> DUPLEX_INTERRUPTED (Barge-in matched)');
      setIsSpeaking(false);
      setIsLoading(false);
      if (speechService.isContinuousSession()) {
        setIsListening(true);
        setAssistantState('listening');
        setModelToast('DUPLEX BARGE-IN // LISTENING');
        setTimeout(() => setModelToast(null), 1500);
      } else {
        setAssistantState('interrupted');
        setModelToast('VOCALIZATION HALTED // INTERRUPTED');
        setTimeout(() => {
          setAssistantState(isEnabled ? 'wake_word_monitoring' : 'idle');
        }, 1000);
      }
    });

    speechService.setAudioLevelCallback((level) => {
      setAudioLevel(level);
    });

    if (isEnabled) {
      setAssistantState('wake_word_monitoring');
      speechService.startWakeWordMode(
        // 1. Full command grasped
        (command) => {
          console.log('[VOICE_STATE_MACHINE] TRANSITION: PROCESSING_AUDIO -> TRANSCRIBING -> THINKING');
          setAssistantState('processing_audio');

          // If continuous ChatGPT voice mode is enabled, start continuous session for subsequent turns
          if (isContinuousEnabled) {
            speechService.startContinuousSession(
              (nextCmd, isFinal) => {
                setSpeechTranscript(nextCmd);
                if (isFinal && nextCmd.trim()) {
                  handleSendMessageRef.current(nextCmd.trim());
                  setSpeechTranscript('');
                  setIsListening(false);
                  setAssistantState('thinking');
                }
              },
              (liveText) => {
                setSpeechTranscript(liveText);
                setIsListening(true);
                setAssistantState('listening');
              }
            );
          }

          setTimeout(() => {
            setAssistantState('transcribing');
            setModelToast(isContinuousEnabled ? 'CHATGPT VOICE ACTIVE // EXECUTING' : 'DIRECTIVE TRANSCRIBED // EXECUTING');
            setTimeout(() => setModelToast(null), 2500);
            setSpeechTranscript('');
            setIsListening(false);
            setAssistantState('thinking');
            handleSendMessageRef.current(command);
          }, 150);
        },
        // 2. Only wake word spoken ("Hey Jarvis" without immediate question)
        () => {
          console.log('[VOICE_STATE_MACHINE] TRANSITION: WAKE_WORD_DETECTED -> SPEAKING ("Yes, Sir?")');
          setModelToast('WAKE-WORD DETECTED // "YES, SIR?"');
          setTimeout(() => setModelToast(null), 3000);
          setIsListening(false);
          setAssistantState('speaking');

          const voiceFeedbackOn = settings?.voice_feedback !== 'false';
          const onSpokenReady = () => {
            console.log('[VOICE_STATE_MACHINE] TRANSITION: SPEAKING -> LISTENING');
            if (isContinuousEnabled) {
              speechService.startContinuousSession(
                (cmd, isFinal) => {
                  setSpeechTranscript(cmd);
                  if (isFinal && cmd.trim()) {
                    handleSendMessageRef.current(cmd.trim());
                    setSpeechTranscript('');
                    setIsListening(false);
                    setAssistantState('thinking');
                  }
                },
                (liveText) => {
                  setSpeechTranscript(liveText);
                  setIsListening(true);
                  setAssistantState('listening');
                }
              );
            } else {
              speechService.startActiveListening(
                (cmd, isFinal) => {
                  setSpeechTranscript(cmd);
                  if (isFinal && cmd.trim()) {
                    handleSendMessageRef.current(cmd.trim());
                    setSpeechTranscript('');
                    setIsListening(false);
                    setAssistantState('thinking');
                    speechService.stopActiveListening();
                  }
                },
                (liveText) => setSpeechTranscript(liveText),
                () => {
                  setSpeechTranscript('');
                  setIsListening(false);
                  setAssistantState(isEnabled ? 'wake_word_monitoring' : 'idle');
                }
              );
            }
            setIsListening(true);
            setAssistantState('listening');
          };

          if (voiceFeedbackOn) {
            speechService.speak('Yes, Sir?', {
              rate: parseFloat(settings?.speech_rate || '1.1'),
              pitch: parseFloat(settings?.speech_pitch || '0.95'),
              preferredVoice: settings?.preferred_voice,
              onEnd: onSpokenReady,
              onError: () => {
                setIsListening(false);
                setAssistantState(isEnabled ? 'wake_word_monitoring' : 'idle');
              },
            });
          } else {
            onSpokenReady();
          }
        },
        // 3. Wake word activated: immediately show reactor listening
        () => {
          console.log('[VOICE_STATE_MACHINE] TRANSITION: WAKE_WORD_MONITORING -> WAKE_WORD_DETECTED -> LISTENING');
          setIsListening(true);
          setAssistantState('wake_word_detected');
          setTimeout(() => {
            setAssistantState('listening');
          }, 350);
          setModelToast('AUDIO INPUT ACTIVE // LISTENING');
        },
        // 4. Live transcript feedback
        (liveText) => {
          setSpeechTranscript(liveText);
          setIsListening(true);
          setAssistantState('listening');
        },
        (err) => {
          console.warn('Wake-word engine notice:', err);
          if (err && err.toLowerCase().includes('micro')) {
            setMicPermissionNeeded(true);
          }
        }
      );
    } else {
      speechService.setWakeWordEnabled(false);
      setAssistantState('idle');
    }

    return () => {
      speechService.setAudioLevelCallback(null);
    };
  }, [
    settings?.wake_word_enabled,
    settings?.continuous_mode,
    settings?.voice_language,
    settings?.vad_silence_timeout,
    settings?.voice_feedback,
    settings?.interrupt_on_wake,
    settings?.max_recording_duration,
    settings?.whisper_backend_enabled,
  ]);

  // Push-to-Talk (PTT) Controls
  const handleStartPushToTalk = () => {
    speechService.interrupt();
    setIsSpeaking(false);
    setSpeechTranscript('');
    speechService.startPushToTalk(
      (transcript, isFinal) => {
        setSpeechTranscript(transcript);
        if (isFinal && transcript.trim()) {
          handleSendMessageRef.current(transcript.trim());
          setSpeechTranscript('');
          setIsListening(false);
          setAssistantState('idle');
        }
      },
      (liveText) => {
        setSpeechTranscript(liveText);
      },
      (error) => {
        console.warn('PTT voice notice:', error);
        setIsListening(false);
        setAssistantState('idle');
      }
    );

    setIsListening(true);
    setAssistantState('listening');
  };

  const handleStopPushToTalk = () => {
    speechService.stopPushToTalk();
    if (speechTranscript.trim()) {
      handleSendMessageRef.current(speechTranscript.trim());
      setSpeechTranscript('');
    }
    setIsListening(false);
    setAssistantState('idle');
  };

  const toggleVoiceMode = async () => {
    const newMode = voiceInputMode === 'click' ? 'push_to_talk' : 'click';
    setVoiceInputMode(newMode);
    try {
      await api.updateSettings({ voice_input_mode: newMode });
      setModelToast(`VOICE PROTOCOL SWITCHED TO ${newMode.toUpperCase()}`);
      setTimeout(() => setModelToast(null), 3000);
    } catch {}
  };

  const toggleWakeWordDirect = async () => {
    const newWake = !wakeWordActive;
    setWakeWordActive(newWake);
    speechService.setWakeWordEnabled(newWake);
    try {
      const updated = await api.updateSettings({ wake_word_enabled: newWake ? 'true' : 'false' });
      setSettings(updated);
      setModelToast(`WAKE-WORD ENGINE: ${newWake ? 'ACTIVE' : 'DEACTIVATED'}`);
      setTimeout(() => setModelToast(null), 3000);
    } catch {}
  };

  // Continuous ChatGPT Voice Mode Handlers
  const startContinuousVoiceMode = () => {
    speechService.interrupt();
    setIsSpeaking(false);
    setSpeechTranscript('');
    setIsListening(true);
    setAssistantState('listening');
    setModelToast('CHATGPT VOICE PROTOCOL ACTIVE // LISTENING');
    setTimeout(() => setModelToast(null), 3000);

    speechService.startContinuousSession(
      (cmd, isFinal) => {
        setSpeechTranscript(cmd);
        if (isFinal && cmd.trim()) {
          handleSendMessageRef.current(cmd.trim());
          setSpeechTranscript('');
          setIsListening(false);
          setAssistantState('thinking');
        }
      },
      (liveText) => {
        setSpeechTranscript(liveText);
        setIsListening(true);
        setAssistantState('listening');
      },
      (err) => {
        console.warn('Continuous voice notice:', err);
      }
    );
  };

  const stopContinuousVoiceMode = (reason: 'user_action' | 'voice_exit' | 'idle_timeout' = 'user_action') => {
    speechService.stopContinuousSession(reason);
    setIsListening(false);
    setSpeechTranscript('');
    setAssistantState(wakeWordActive ? 'wake_word_monitoring' : 'idle');
    setModelToast('VOICE PROTOCOL RETURNED TO STANDBY');
    setTimeout(() => setModelToast(null), 2500);
  };

  // Global ESC Key Listener to stop vocalization or exit continuous voice mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (speechService.isSpeakingNow()) {
          speechService.stopSpeaking();
          setIsSpeaking(false);
          setIsListening(true);
          setAssistantState('listening');
          setModelToast('VOCALIZATION HALTED [ESC] // LISTENING');
          setTimeout(() => setModelToast(null), 2000);
          return;
        }
        if (speechService.isContinuousSession()) {
          stopContinuousVoiceMode('user_action');
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [wakeWordActive]);

  // Voice Controls (Arc Reactor / Mic Button Click-To-Talk)
  const toggleVoice = () => {
    // Interruption: silence any ongoing speech immediately
    speechService.interrupt();
    setIsSpeaking(false);
    activateMicrophone();

    // If continuous mode is running, clicking Arc Reactor deactivates it:
    if (speechService.isContinuousSession()) {
      stopContinuousVoiceMode('user_action');
      return;
    }

    if (isListening) {
      speechService.stopActiveListening();
      if (speechTranscript.trim()) {
        handleSendMessageRef.current(speechTranscript.trim());
        setSpeechTranscript('');
      }
      setIsListening(false);
      setAssistantState(wakeWordActive ? 'wake_word_monitoring' : 'idle');
    } else {
      setSpeechTranscript('');
      const isContinuousEnabled = settings?.continuous_mode !== 'false';
      if (isContinuousEnabled) {
        startContinuousVoiceMode();
      } else {
        speechService.startActiveListening(
          (transcript, isFinal) => {
            setSpeechTranscript(transcript);
            if (isFinal && transcript.trim()) {
              handleSendMessageRef.current(transcript.trim());
              setSpeechTranscript('');
              speechService.stopActiveListening();
              setIsListening(false);
              setAssistantState('thinking');
            }
          },
          (liveText) => {
            setSpeechTranscript(liveText);
          },
          () => {
            setSpeechTranscript('');
            setIsListening(false);
            setAssistantState(wakeWordActive ? 'wake_word_monitoring' : 'idle');
            setModelToast('AUDIO INPUT TIMED OUT // STANDBY');
            setTimeout(() => setModelToast(null), 2500);
          },
          (error) => {
            console.warn('Voice error:', error);
            setIsListening(false);
            setAssistantState(wakeWordActive ? 'wake_word_monitoring' : 'idle');
          }
        );

        setIsListening(true);
        setAssistantState('listening');
      }
    }
  };

  const handleStopSpeaking = () => {
    speechService.stopSpeaking();
    setIsSpeaking(false);
    if (assistantState === 'speaking') {
      setAssistantState('idle');
    }
  };

  const handleToggleMute = () => {
    const muted = speechService.toggleMute();
    setIsMuted(muted);
  };

  const handleSaveSettings = async (newSettings: Partial<SystemSettings>) => {
    const updated = await api.updateSettings(newSettings);
    setSettings(updated);
    refreshTelemetry();
    const provName = (newSettings.provider || updated.provider || 'ollama').toUpperCase();
    setModelToast(`NEURAL CORE ACTIVATED: ${provName}`);
    setTimeout(() => setModelToast(null), 3500);
  };

  const currentActiveModel = 'jarvis-latest-fast';

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden' }}>
      <div className="scanlines" />

      {/* Sidebar Navigation */}
      {showSidebar && (
        <Sidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={selectConversation}
          onNewConversation={startNewConversation}
          onDeleteConversation={deleteConversation}
          onClearAll={clearAllConversations}
          ollamaHealth={ollamaHealth}
          systemStatus={systemStatus}
          activeModel={currentActiveModel}
          activeProvider={settings?.provider || 'ollama'}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onOpenMemories={() => setIsMemoriesOpen(true)}
        />
      )}

      {/* Main Command Center */}
      <main
        style={{
          flex: 1,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          overflow: 'hidden',
          background: 'radial-gradient(ellipse at 50% 15%, rgba(0, 112, 243, 0.08) 0%, transparent 60%)',
        }}
      >
        {/* Top HUD Bar */}
        <header
          style={{
            height: '52px',
            padding: '0 20px',
            borderBottom: '1px solid var(--cyan-border)',
            background: 'rgba(5, 12, 28, 0.75)',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            zIndex: 20,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              title="Toggle sidebar"
              style={{ background: 'none', border: 'none', color: '#00f0ff', cursor: 'pointer' }}
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="font-hud" style={{ fontSize: '15px', letterSpacing: '1px', color: '#f8fafc' }}>
              MARK III AI COMMAND TERMINAL
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Active Provider & Model Indicator Badge */}
            <div
              className="cyber-card"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                background: settings?.provider === 'gemini' ? 'rgba(168, 85, 247, 0.12)' : 'rgba(0, 240, 255, 0.08)',
                border: settings?.provider === 'gemini' ? '1px solid rgba(168, 85, 247, 0.5)' : '1px solid rgba(0, 240, 255, 0.35)',
                borderRadius: '6px',
                transition: 'all 0.2s ease',
              }}
            >
              {settings?.provider === 'gemini' ? (
                <Cloud className="w-3.5 h-3.5 text-[#c084fc]" />
              ) : (
                <Cpu className="w-3.5 h-3.5 text-[#00f0ff]" />
              )}
              <span className="font-tech" style={{ fontSize: '11px', color: settings?.provider === 'gemini' ? '#c084fc' : '#38bdf8', fontWeight: 600 }}>
                {settings?.provider === 'gemini' ? 'CORE: GEMINI [CLOUD]' : 'CORE: OLLAMA [LOCAL]'}
              </span>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: settings?.provider === 'gemini' ? '#e9d5ff' : '#00f0ff',
                  marginLeft: '2px',
                }}
              >
                {currentActiveModel}
              </span>
            </div>

            {/* ChatGPT Continuous Voice Mode Active Badge */}
            {isContinuousVoiceActive && (
              <button
                type="button"
                onClick={() => stopContinuousVoiceMode('user_action')}
                title="Continuous Voice active (ChatGPT Mode). Click or press ESC to end."
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '4px 10px',
                  background: 'rgba(0, 255, 170, 0.22)',
                  border: '1px solid #00ffaa',
                  boxShadow: '0 0 12px rgba(0, 255, 170, 0.4)',
                  borderRadius: '6px',
                  color: '#00ffaa',
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  cursor: 'pointer',
                  fontWeight: 600,
                  transition: 'all 0.15s ease',
                }}
              >
                <span className="w-2 h-2 rounded-full bg-[#00ffaa] animate-ping" />
                <span>CHATGPT VOICE: ACTIVE [END (ESC)]</span>
              </button>
            )}

            {/* Quick Wake-Word HUD Toggle */}
            <button
              type="button"
              onClick={toggleWakeWordDirect}
              title="Click to toggle continuous 'Hey Jarvis' wake-word detection"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                background: wakeWordActive ? 'rgba(0, 255, 170, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                border: wakeWordActive ? '1px solid #00ffaa' : '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '6px',
                color: wakeWordActive ? '#00ffaa' : '#94a3b8',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <span className={`w-2 h-2 rounded-full ${wakeWordActive ? 'bg-[#00ffaa] animate-ping' : 'bg-slate-500'}`} />
              <span>WAKE: {wakeWordActive ? 'HEY JARVIS' : 'OFF'}</span>
            </button>

            {/* Connection & Cloud Indicator */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
              {settings?.provider === 'gemini' ? (
                <>
                  <Cloud className="w-4 h-4 text-[#a855f7]" />
                  <span className="font-tech" style={{ color: '#c084fc', fontWeight: 600 }}>
                    GEMINI CLOUD ENGAGED
                  </span>
                </>
              ) : (
                <>
                  {ollamaHealth?.connected ? (
                    <Wifi className="w-4 h-4 text-[#00ffaa]" />
                  ) : (
                    <WifiOff className="w-4 h-4 text-[#ef4444]" />
                  )}
                  <span className="font-tech" style={{ color: ollamaHealth?.connected ? '#00ffaa' : '#ef4444' }}>
                    {ollamaHealth?.connected ? 'LOCAL AI ONLINE' : 'OLLAMA OFFLINE'}
                  </span>
                </>
              )}
            </div>

            {/* Clock */}
            <div
              className="font-hud"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: '#00f0ff',
                fontSize: '13px',
                letterSpacing: '1px',
              }}
            >
              <Clock className="w-4 h-4" />
              <span>{currentTimeStr}</span>
            </div>
          </div>
        </header>

        {/* Dynamic Model Switch Toast Notification */}
        {modelToast && (
          <div
            style={{
              position: 'absolute',
              top: '64px',
              right: '24px',
              zIndex: 100,
              background: 'rgba(5, 12, 28, 0.95)',
              border: '1px solid #00f0ff',
              boxShadow: '0 0 20px rgba(0, 240, 255, 0.4)',
              borderRadius: '6px',
              padding: '10px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: '#00f0ff',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              letterSpacing: '1px',
              animation: 'fadeIn 0.2s ease-out',
            }}
          >
            <CheckCircle className="w-4 h-4 text-[#00ffaa]" />
            <span>{modelToast}</span>
          </div>
        )}

        {/* Microphone Permission Required Notification Banner */}
        {micPermissionNeeded && (
          <div
            onClick={activateMicrophone}
            title="Click to initialize microphone sensors"
            style={{
              position: 'absolute',
              top: '64px',
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 100,
              background: 'rgba(239, 68, 68, 0.25)',
              border: '1px solid #ef4444',
              boxShadow: '0 0 25px rgba(239, 68, 68, 0.45)',
              borderRadius: '8px',
              padding: '10px 20px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              cursor: 'pointer',
              color: '#fecaca',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              letterSpacing: '1px',
              animation: 'fadeIn 0.2s ease-out',
            }}
          >
            <Mic className="w-4 h-4 text-[#ef4444] animate-pulse" />
            <span style={{ fontWeight: 600 }}>AUDIO SENSORS STANDBY — CLICK TO ACTIVATE MICROPHONE</span>
          </div>
        )}

        {/* Center Display: Arc Reactor Visualizer */}
        <div style={{ padding: '8px 20px', display: 'flex', justifyContent: 'center' }}>
          <ArcReactor
            state={isSpeaking ? 'speaking' : assistantState}
            onToggleVoice={toggleVoice}
            isListening={!isSpeaking && isListening}
            isSpeaking={isSpeaking}
            isContinuousVoiceActive={isContinuousVoiceActive}
            audioLevel={isSpeaking ? 0 : audioLevel}
            currentToolName={currentToolName}
            modelName={currentActiveModel}
          />
        </div>

        {/* Message Stream Viewport */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '10px 24px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {messages.length === 0 ? (
            <div
              style={{
                margin: 'auto',
                textAlign: 'center',
                maxWidth: '480px',
                padding: '24px',
                borderRadius: '8px',
                background: 'rgba(10, 20, 42, 0.4)',
                border: '1px dashed var(--cyan-border)',
              }}
            >
              <h2 className="font-hud" style={{ fontSize: '20px', color: '#00f0ff', marginBottom: '8px' }}>
                JARVIS IS STANDING BY
              </h2>
              <p style={{ color: '#94a3b8', fontSize: '14px', lineHeight: '1.6' }}>
                Powered by your local RTX 3050 and <code>qwen3:4b</code>. You may type a query below, click the Arc Reactor to activate voice recognition, or select a direct protocol tool.
              </p>
            </div>
          ) : (
            messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Interactive Console */}
        <footer
          style={{
            padding: '12px 24px 16px',
            borderTop: '1px solid rgba(0, 240, 255, 0.15)',
            background: 'rgba(5, 12, 28, 0.85)',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          {/* Quick Tools Row */}
          <QuickTools onQuickCommand={handleSendMessage} isLoading={isLoading} />

          {/* Chat and Voice Input */}
          <ChatInput
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            isListening={isListening}
            isSpeaking={isSpeaking}
            transcript={speechTranscript}
            isMuted={isMuted}
            voiceInputMode={voiceInputMode}
            audioLevel={audioLevel}
            onToggleVoice={toggleVoice}
            onStartPushToTalk={handleStartPushToTalk}
            onStopPushToTalk={handleStopPushToTalk}
            onStopSpeaking={handleStopSpeaking}
            onToggleMute={handleToggleMute}
            onToggleVoiceMode={toggleVoiceMode}
          />
        </footer>
      </main>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settings={settings}
        ollamaHealth={ollamaHealth}
        onSave={handleSaveSettings}
        onRefreshHealth={refreshTelemetry}
      />

      {/* Memory Manager Modal */}
      <MemoryManager isOpen={isMemoriesOpen} onClose={() => setIsMemoriesOpen(false)} />
    </div>
  );
};

export default App;
