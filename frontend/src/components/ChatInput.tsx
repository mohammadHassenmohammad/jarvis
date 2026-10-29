import React, { useState, useRef, useEffect } from 'react';
import { Send, Mic, MicOff, Square, Volume2, VolumeX, Radio } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  isListening: boolean;
  isSpeaking: boolean;
  transcript: string;
  isMuted: boolean;
  voiceInputMode?: 'click' | 'push_to_talk';
  audioLevel?: number;
  onToggleVoice: () => void;
  onStartPushToTalk?: () => void;
  onStopPushToTalk?: () => void;
  onStopSpeaking: () => void;
  onToggleMute: () => void;
  onToggleVoiceMode?: () => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading,
  isListening,
  isSpeaking,
  transcript,
  isMuted,
  voiceInputMode = 'click',
  audioLevel = 0,
  onToggleVoice,
  onStartPushToTalk,
  onStopPushToTalk,
  onStopSpeaking,
  onToggleMute,
  onToggleVoiceMode,
}) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isPttPressedRef = useRef(false);
  const prevTranscriptRef = useRef(transcript);

  // Sync speech transcript into input while speaking, and clear input when transcript resets
  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    } else if (prevTranscriptRef.current && !transcript) {
      setInput('');
    }
    prevTranscriptRef.current = transcript;
  }, [transcript]);

  // Cleanly clear textbox whenever message begins sending or loading
  useEffect(() => {
    if (isLoading) {
      setInput('');
    }
  }, [isLoading]);

  // Global Keyboard shortcuts: Escape to Interrupt speech, Space for Push-to-Talk (when not in text input)
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Escape key immediately interrupts any ongoing speech
      if (e.key === 'Escape' && isSpeaking) {
        e.preventDefault();
        onStopSpeaking();
      }

      // Spacebar Push-to-Talk when not actively typing in an input/textarea
      if (
        voiceInputMode === 'push_to_talk' &&
        e.code === 'Space' &&
        document.activeElement?.tagName !== 'INPUT' &&
        document.activeElement?.tagName !== 'TEXTAREA' &&
        !isPttPressedRef.current
      ) {
        e.preventDefault();
        isPttPressedRef.current = true;
        onStartPushToTalk?.();
      }
    };

    const handleGlobalKeyUp = (e: KeyboardEvent) => {
      if (voiceInputMode === 'push_to_talk' && e.code === 'Space' && isPttPressedRef.current) {
        e.preventDefault();
        isPttPressedRef.current = false;
        onStopPushToTalk?.();
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    window.addEventListener('keyup', handleGlobalKeyUp);
    return () => {
      window.removeEventListener('keydown', handleGlobalKeyDown);
      window.removeEventListener('keyup', handleGlobalKeyUp);
    };
  }, [isSpeaking, voiceInputMode, onStopSpeaking, onStartPushToTalk, onStopPushToTalk]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;
    const textToSend = input.trim();
    setInput('');
    onSendMessage(textToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // If JARVIS is speaking and user starts typing, interrupt immediately
    if (isSpeaking) {
      onStopSpeaking();
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleMicMouseDown = () => {
    if (voiceInputMode === 'push_to_talk') {
      isPttPressedRef.current = true;
      onStartPushToTalk?.();
    }
  };

  const handleMicMouseUp = () => {
    if (voiceInputMode === 'push_to_talk' && isPttPressedRef.current) {
      isPttPressedRef.current = false;
      onStopPushToTalk?.();
    }
  };

  const handleMicClick = () => {
    if (voiceInputMode === 'click') {
      onToggleVoice();
    }
  };

  const isMicActive = !isSpeaking && isListening;

  return (
    <div style={{ width: '100%', position: 'relative' }}>
      {/* Speech Recognition & Audio Visualizer Floating Toast */}
      {isMicActive && (
        <div
          style={{
            position: 'absolute',
            top: '-46px',
            left: '0',
            right: '0',
            background: 'rgba(10, 25, 48, 0.92)',
            border: '1px solid #00ffaa',
            backdropFilter: 'blur(10px)',
            borderRadius: '6px',
            padding: '6px 14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 0 15px rgba(0, 255, 170, 0.3)',
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className="w-2.5 h-2.5 rounded-full bg-[#00ffaa] animate-ping" />
            <span className="font-tech" style={{ color: '#00ffaa', fontSize: '12px', letterSpacing: '1px' }}>
              {voiceInputMode === 'push_to_talk' ? 'PUSH-TO-TALK ACTIVE (RELEASE TO SEND):' : 'VOICE STREAM ACTIVE:'}
            </span>
            <span style={{ color: '#f8fafc', fontStyle: 'italic', fontSize: '13px' }}>
              {transcript || 'Listening for speech input...'}
            </span>
          </div>

          {/* Real-time Decibel Audio Equalizer Bars */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '3px', height: '18px', paddingLeft: '12px' }}>
            {[0.5, 0.9, 1.4, 0.8, 1.1, 0.6].map((multiplier, idx) => (
              <div
                key={idx}
                style={{
                  width: '3px',
                  height: `${Math.max(4, Math.min(20, (audioLevel || 0.15) * 26 * multiplier))}px`,
                  background: '#00ffaa',
                  borderRadius: '1px',
                  transition: 'height 0.06s ease',
                  boxShadow: '0 0 4px #00ffaa',
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Main Input Panel */}
      <div
        className="cyber-card"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 12px',
          background: 'rgba(10, 18, 38, 0.88)',
          border: '1px solid var(--cyan-border)',
          borderRadius: '8px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.6), inset 0 0 10px rgba(0, 240, 255, 0.05)',
        }}
      >
        {/* Mic Control Button with PTT / Click-To-Talk Support */}
        <button
          type="button"
          onClick={handleMicClick}
          onMouseDown={handleMicMouseDown}
          onMouseUp={handleMicMouseUp}
          onTouchStart={handleMicMouseDown}
          onTouchEnd={handleMicMouseUp}
          title={
            isSpeaking
              ? 'JARVIS is speaking. Press ESC or click INTERRUPT to speak'
              : voiceInputMode === 'push_to_talk'
              ? 'Hold to Speak (Push-to-Talk) or Hold Spacebar'
              : isMicActive
              ? 'Click to stop recording'
              : 'Click to start voice recognition'
          }
          style={{
            background: isMicActive
              ? 'rgba(0, 255, 170, 0.25)'
              : 'rgba(0, 240, 255, 0.1)',
            border: isMicActive ? '1.5px solid #00ffaa' : '1px solid rgba(0, 240, 255, 0.3)',
            borderRadius: '6px',
            width: '42px',
            height: '42px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            color: isMicActive ? '#00ffaa' : '#00f0ff',
            boxShadow: isMicActive ? '0 0 15px rgba(0, 255, 170, 0.6)' : 'none',
            transition: 'all 0.15s ease',
            userSelect: 'none',
          }}
        >
          {isMicActive ? <MicOff className="w-5 h-5 animate-pulse" /> : <Mic className="w-5 h-5" />}
        </button>

        {/* PTT Mode Switcher Pill */}
        {onToggleVoiceMode && (
          <button
            type="button"
            onClick={onToggleVoiceMode}
            title={`Current voice input mode: ${voiceInputMode.toUpperCase()}. Click to switch mode.`}
            style={{
              background: voiceInputMode === 'push_to_talk' ? 'rgba(255, 183, 3, 0.15)' : 'rgba(0, 240, 255, 0.08)',
              border: voiceInputMode === 'push_to_talk' ? '1px solid #ffb703' : '1px solid rgba(0, 240, 255, 0.25)',
              borderRadius: '4px',
              padding: '3px 6px',
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              color: voiceInputMode === 'push_to_talk' ? '#ffb703' : '#38bdf8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              whiteSpace: 'nowrap',
            }}
          >
            <Radio className="w-3 h-3" />
            <span>{voiceInputMode === 'push_to_talk' ? 'PTT' : 'VOX'}</span>
          </button>
        )}

        {/* Text Area */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isSpeaking
              ? 'JARVIS is speaking... Press ESC or click INTERRUPT to speak...'
              : isLoading
              ? 'JARVIS is thinking...'
              : isListening
              ? 'Listening attentively... speak naturally or say "stop"...'
              : voiceInputMode === 'push_to_talk'
              ? 'Enter command, hold Space or Mic to speak, or type...'
              : 'Enter command or question for JARVIS...'
          }
          disabled={isLoading}
          rows={1}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: '#f8fafc',
            fontFamily: 'var(--font-body)',
            fontSize: '15px',
            resize: 'none',
            padding: '6px 4px',
            maxHeight: '120px',
          }}
        />

        {/* Immediate Silence / Interruption Button (Active when JARVIS is vocalizing) */}
        {isSpeaking && (
          <button
            type="button"
            onClick={onStopSpeaking}
            title="Silence JARVIS voice output immediately (Shortcut: ESC)"
            style={{
              background: 'rgba(255, 0, 85, 0.25)',
              border: '1px solid #ff0055',
              borderRadius: '6px',
              padding: '6px 12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: '#ff3366',
              cursor: 'pointer',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 'bold',
              boxShadow: '0 0 12px rgba(255, 0, 85, 0.5)',
              animation: 'pulse 1.5s infinite',
            }}
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            <span>INTERRUPT (ESC)</span>
          </button>
        )}

        {/* Audio Mute/Unmute Toggle */}
        <button
          type="button"
          onClick={onToggleMute}
          title={isMuted ? 'Unmute speech output' : 'Mute speech output'}
          style={{
            background: 'transparent',
            border: 'none',
            color: isMuted ? '#ef4444' : '#94a3b8',
            cursor: 'pointer',
            padding: '6px',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
        </button>

        {/* Send Button */}
        <button
          type="button"
          onClick={() => handleSubmit()}
          disabled={!input.trim() || isLoading}
          style={{
            background: input.trim() && !isLoading ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)',
            border: input.trim() && !isLoading ? '1px solid #00f0ff' : '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '6px',
            width: '42px',
            height: '42px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
            color: input.trim() && !isLoading ? '#00f0ff' : '#475569',
            boxShadow: input.trim() && !isLoading ? '0 0 12px rgba(0, 240, 255, 0.3)' : 'none',
            transition: 'all 0.15s ease',
          }}
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
