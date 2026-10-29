import React from 'react';
import type { AssistantState } from '../types';
import { Mic, Volume2, Cpu, Wrench, Radio, Zap, FileText, AlertTriangle, Square, Layers } from 'lucide-react';

interface ArcReactorProps {
  state: AssistantState;
  onToggleVoice: () => void;
  isListening: boolean;
  isContinuousVoiceActive?: boolean;
  audioLevel?: number;
  currentToolName?: string;
  modelName?: string;
}

export const ArcReactor: React.FC<ArcReactorProps> = ({
  state,
  onToggleVoice,
  isListening,
  isContinuousVoiceActive = false,
  audioLevel = 0,
  currentToolName,
  modelName,
}) => {
  const getStateInfo = () => {
    switch (state) {
      case 'wake_word_monitoring':
        return {
          title: 'WAKE-WORD PROTOCOL ACTIVE',
          status: 'MONITORING AUDIO FOR "HEY JARVIS"',
          color: '#00f0ff',
          glowClass: 'pulse-glow-anim',
          icon: <Radio className="w-8 h-8 text-[#00f0ff] animate-pulse" />,
        };
      case 'wake_word_detected':
        return {
          title: 'WAKE-WORD RECOGNIZED',
          status: 'INITIALIZING ACOUSTIC PROTOCOL',
          color: '#38bdf8',
          glowClass: 'listening-anim',
          icon: <Zap className="w-8 h-8 text-[#38bdf8] animate-bounce" />,
        };
      case 'listening':
        return {
          title: isContinuousVoiceActive ? 'CHATGPT VOICE PROTOCOL ACTIVE' : 'ACOUSTIC RECEPTOR ACTIVE',
          status: isContinuousVoiceActive ? 'HANDS-FREE LISTENING // SPEAK FREELY' : 'LISTENING FOR SPOKEN DIRECTIVE',
          color: '#00ffaa',
          glowClass: 'listening-anim',
          icon: <Mic className="w-8 h-8 text-[#00ffaa] animate-pulse" />,
        };
      case 'processing_audio':
        return {
          title: 'AUDIO BUFFER LOCKED',
          status: 'EVALUATING VOICE ACTIVITY & CADENCE',
          color: '#a855f7',
          glowClass: 'pulse-glow-anim',
          icon: <Layers className="w-8 h-8 text-[#a855f7] animate-spin" />,
        };
      case 'transcribing':
        return {
          title: 'NEURAL SPEECH TRANSCRIBER',
          status: 'CONVERTING AUDIO STREAM TO TEXT',
          color: '#06b6d4',
          glowClass: 'spin-fast',
          icon: <FileText className="w-8 h-8 text-[#06b6d4] animate-pulse" />,
        };
      case 'thinking':
        return {
          title: `${(modelName || 'JARVIS').toUpperCase()} NEURAL CORE`,
          status: 'PROCESSING DIRECTIVE',
          color: '#ffb703',
          glowClass: 'pulse-glow-anim',
          icon: <Cpu className="w-8 h-8 text-[#ffb703] animate-spin" />,
        };
      case 'speaking':
        return {
          title: 'AUDIO SYNTHESIZER',
          status: 'SPEAKING VOCAL RESPONSE',
          color: '#00f0ff',
          glowClass: 'speaking-anim',
          icon: <Volume2 className="w-8 h-8 text-[#00f0ff] animate-bounce" />,
        };
      case 'interrupted':
        return {
          title: 'INTERRUPTION PROTOCOL',
          status: 'VOCAL OUTPUT HALTED // LISTENING',
          color: '#f43f5e',
          glowClass: 'pulse-glow-anim',
          icon: <Square className="w-8 h-8 text-[#f43f5e]" />,
        };
      case 'executing_tool':
        return {
          title: 'SYSTEM TOOL EXECUTOR',
          status: currentToolName ? `RUNNING: ${currentToolName}` : 'EXECUTING ALLOWLISTED ACTION',
          color: '#38bdf8',
          glowClass: 'spin-fast',
          icon: <Wrench className="w-8 h-8 text-[#38bdf8] animate-spin" />,
        };
      case 'error':
        return {
          title: 'AUDIO SUBSYSTEM NOTICE',
          status: 'DIAGNOSTIC NOTICE DETECTED',
          color: '#ef4444',
          glowClass: 'pulse-glow-anim',
          icon: <AlertTriangle className="w-8 h-8 text-[#ef4444] animate-bounce" />,
        };
      case 'idle':
      default:
        return {
          title: 'JARVIS MARK III',
          status: 'SYSTEM STANDBY // READY',
          color: '#00f0ff',
          glowClass: 'pulse-glow-anim',
          icon: <Radio className="w-8 h-8 text-[#00f0ff]" />,
        };
    }
  };

  const info = getStateInfo();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '16px 0' }}>
      {/* Reactor Housing */}
      <div
        onClick={onToggleVoice}
        title={isListening ? 'Click to stop listening' : 'Click to speak to JARVIS'}
        className={`relative cursor-pointer transition-all duration-150 ${info.glowClass}`}
        style={{
          width: '180px',
          height: '180px',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'radial-gradient(circle, rgba(10,25,50,0.85) 0%, rgba(5,10,20,0.95) 70%, #030712 100%)',
          border: `2px solid ${info.color}`,
          transform: isListening ? `scale(${1 + Math.min(0.2, audioLevel * 0.25)})` : 'none',
          boxShadow: isListening
            ? `0 0 ${25 + audioLevel * 45}px #00ffaa, inset 0 0 ${20 + audioLevel * 30}px #00ffaa`
            : `0 0 25px ${info.color}40, inset 0 0 20px ${info.color}30`,
        }}
      >
        {/* Outer Rotating Segment Ring */}
        <svg
          viewBox="0 0 100 100"
          className="absolute inset-0 w-full h-full spin-clockwise"
          style={{ opacity: 0.7 }}
        >
          <circle
            cx="50"
            cy="50"
            r="46"
            fill="none"
            stroke={info.color}
            strokeWidth="1.5"
            strokeDasharray="4 8 16 8"
          />
          <circle
            cx="50"
            cy="50"
            r="41"
            fill="none"
            stroke={info.color}
            strokeWidth="0.8"
            strokeDasharray="2 4"
          />
        </svg>

        {/* Counter Rotating Ring */}
        <svg
          viewBox="0 0 100 100"
          className="absolute inset-0 w-full h-full spin-counter-clockwise"
          style={{ opacity: 0.55 }}
        >
          <circle
            cx="50"
            cy="50"
            r="35"
            fill="none"
            stroke="#0088ff"
            strokeWidth="2"
            strokeDasharray="14 10"
          />
          <polygon
            points="50,18 52,22 48,22"
            fill={info.color}
          />
          <polygon
            points="50,82 52,78 48,78"
            fill={info.color}
          />
          <polygon
            points="18,50 22,52 22,48"
            fill={info.color}
          />
          <polygon
            points="82,50 78,52 78,48"
            fill={info.color}
          />
        </svg>

        {/* Core Center Reactor Chamber */}
        <div
          style={{
            width: '84px',
            height: '84px',
            borderRadius: '50%',
            background: `radial-gradient(circle, ${info.color}35 0%, rgba(5,15,35,0.9) 70%)`,
            border: `1.5px solid ${info.color}`,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 0 18px ${info.color}60`,
            zIndex: 10,
          }}
        >
          {info.icon}
        </div>
      </div>

      {/* Telemetry Labels */}
      <div style={{ textAlign: 'center', marginTop: '12px' }}>
        <div
          className="font-hud"
          style={{
            fontSize: '14px',
            letterSpacing: '3px',
            color: info.color,
            textShadow: `0 0 8px ${info.color}80`,
          }}
        >
          {info.title}
        </div>
        <div
          className="font-tech"
          style={{
            fontSize: '12px',
            letterSpacing: '1.5px',
            color: '#94a3b8',
            marginTop: '2px',
          }}
        >
          {info.status}
        </div>
      </div>
    </div>
  );
};
