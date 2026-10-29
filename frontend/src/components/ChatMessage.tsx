import React, { useState } from 'react';
import type { Message } from '../types';
import { Bot, User, Wrench, Copy, Check, Volume2, Cpu, ExternalLink } from 'lucide-react';
import { speechService } from '../services/speech';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const [copied, setCopied] = useState(false);
  const [showThinking, setShowThinking] = useState(false);

  const isUser = message.role === 'user';
  const isTool = message.role === 'tool';
  const urlMatch = message.content.match(/(https?:\/\/[^\s)]+)/);
  const detectedUrl = urlMatch ? urlMatch[0].replace(/[.,!?;:]$/, '') : null;

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSpeak = () => {
    if (speechService.isSpeakingNow()) {
      speechService.stopSpeaking();
    } else {
      speechService.speak(message.content);
    }
  };

  if (isTool) {
    return (
      <div
        style={{
          margin: '8px 0',
          padding: '8px 12px',
          background: 'rgba(15, 23, 42, 0.6)',
          borderLeft: '3px solid #38bdf8',
          borderRadius: '4px',
          fontSize: '12px',
          fontFamily: 'var(--font-mono)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8', marginBottom: '4px' }}>
          <Wrench className="w-3.5 h-3.5" />
          <span style={{ fontWeight: 600 }}>SYSTEM TOOL EXECUTION REPORT</span>
        </div>
        <div style={{ color: '#cbd5e1', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {message.content}
        </div>
        {detectedUrl && (
          <div style={{ marginTop: '8px' }}>
            <a
              href={detectedUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '5px 12px',
                background: 'rgba(0, 240, 255, 0.15)',
                border: '1px solid #00f0ff',
                borderRadius: '4px',
                color: '#00f0ff',
                textDecoration: 'none',
                fontWeight: 600,
                fontSize: '11px',
                letterSpacing: '0.5px',
                boxShadow: '0 0 8px rgba(0, 240, 255, 0.25)',
                cursor: 'pointer',
              }}
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>OPEN WEBSITE: {detectedUrl.replace(/^https?:\/\/(www\.)?/, '').split('/')[0].toUpperCase()} ↗</span>
            </a>
          </div>
        )}
      </div>
    );
  }

  const isGenerating = !isUser && !message.content;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        margin: '12px 0',
        width: '100%',
      }}
    >
      {/* Sender Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          marginBottom: '4px',
          fontSize: '11px',
          fontFamily: 'var(--font-display)',
          letterSpacing: '1px',
          color: isUser ? '#38bdf8' : '#00f0ff',
        }}
      >
        {isUser ? (
          <>
            <span>USER // COMMAND</span>
            <User className="w-3.5 h-3.5" />
          </>
        ) : (
          <>
            <Bot className="w-3.5 h-3.5" />
            <span>J.A.R.V.I.S. // AI PROTOCOL</span>
          </>
        )}
      </div>

      {/* Message Card */}
      <div
        className="cyber-card"
        style={{
          maxWidth: '85%',
          padding: '12px 16px',
          background: isUser ? 'rgba(0, 112, 243, 0.15)' : 'rgba(10, 25, 48, 0.8)',
          border: isUser ? '1px solid rgba(0, 112, 243, 0.4)' : '1px solid var(--cyan-border)',
          borderRadius: '6px',
          color: '#f8fafc',
          lineHeight: '1.6',
        }}
      >
        {/* Thinking Collapsible (if available) */}
        {message.thinking && (
          <div
            style={{
              marginBottom: '10px',
              padding: '6px 10px',
              background: 'rgba(255, 183, 3, 0.08)',
              border: '1px solid rgba(255, 183, 3, 0.25)',
              borderRadius: '4px',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <div
              onClick={() => setShowThinking(!showThinking)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                color: '#ffb703',
              }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Cpu className="w-3 h-3 animate-spin" />
                {showThinking ? 'HIDE NEURAL REASONING' : 'VIEW NEURAL REASONING'}
              </span>
            </div>
            {showThinking && (
              <div style={{ marginTop: '8px', color: '#fed7aa', whiteSpace: 'pre-wrap', maxHeight: '180px', overflowY: 'auto' }}>
                {message.thinking}
              </div>
            )}
          </div>
        )}

        {/* Tool Call Badges */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div style={{ marginBottom: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {message.tool_calls.map((tc, idx) => (
              <span
                key={idx}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '3px 8px',
                  background: 'rgba(0, 240, 255, 0.12)',
                  border: '1px solid rgba(0, 240, 255, 0.4)',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  color: '#38bdf8',
                }}
              >
                <Wrench className="w-3 h-3 text-[#38bdf8]" />
                Tool Called: {tc.function.name}
              </span>
            ))}
          </div>
        )}

        {/* Content Body */}
        {isGenerating ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: '#38bdf8',
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              padding: '4px 0',
            }}
          >
            <span className="w-2 h-2 rounded-full bg-[#00f0ff] animate-ping" />
            <span>Formulating response...</span>
          </div>
        ) : (
          <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '15px' }}>
            {message.content}
          </div>
        )}

        {/* Action Toolbar */}
        {!isUser && message.content && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginTop: '8px',
              paddingTop: '6px',
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              fontSize: '11px',
              color: '#94a3b8',
            }}
          >
            <button
              onClick={handleSpeak}
              title="Vocalize this response"
              style={{ background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              <Volume2 className="w-3.5 h-3.5" />
              <span>Voice</span>
            </button>
            <button
              onClick={handleCopy}
              title="Copy text"
              style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
