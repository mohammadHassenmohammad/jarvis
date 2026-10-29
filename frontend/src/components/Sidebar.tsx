import React from 'react';
import type { Conversation, OllamaHealth, SystemStatus } from '../types';
import { Plus, Trash2, Cpu, HardDrive, Settings, Database, Activity } from 'lucide-react';

interface SidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: string) => void;
  onClearAll: () => void;
  ollamaHealth: OllamaHealth | null;
  systemStatus: SystemStatus | null;
  activeModel?: string;
  activeProvider?: string;
  onOpenSettings: () => void;
  onOpenMemories: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onClearAll,
  ollamaHealth,
  systemStatus,
  activeModel,
  activeProvider = 'ollama',
  onOpenSettings,
  onOpenMemories,
}) => {
  const isGemini = activeProvider === 'gemini';
  return (
    <aside
      className="cyber-card"
      style={{
        width: '300px',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 0,
        borderRight: '1px solid var(--cyan-border)',
        borderTop: 'none',
        borderBottom: 'none',
        borderLeft: 'none',
        background: 'rgba(5, 12, 28, 0.92)',
        zIndex: 50,
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: '16px',
          borderBottom: '1px solid rgba(0, 240, 255, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: ollamaHealth?.connected ? '#00ffaa' : '#ef4444',
              boxShadow: ollamaHealth?.connected ? '0 0 10px #00ffaa' : '0 0 10px #ef4444',
            }}
          />
          <h1
            className="font-hud"
            style={{
              fontSize: '17px',
              letterSpacing: '2px',
              color: '#00f0ff',
              textShadow: '0 0 10px rgba(0,240,255,0.4)',
            }}
          >
            J.A.R.V.I.S.
          </h1>
        </div>
        <span
          className="font-tech"
          style={{
            fontSize: '11px',
            color: '#38bdf8',
            padding: '2px 6px',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '3px',
          }}
        >
          v1.0 OS
        </span>
      </div>

      {/* New Session Button */}
      <div style={{ padding: '12px 16px' }}>
        <button
          onClick={onNewConversation}
          className="cyber-button"
          style={{ width: '100%', justifyContent: 'center' }}
        >
          <Plus className="w-4 h-4" />
          <span>New Session</span>
        </button>
      </div>

      {/* Conversation List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '0 12px',
        }}
      >
        <div
          className="font-tech"
          style={{
            fontSize: '11px',
            color: '#64748b',
            letterSpacing: '1px',
            padding: '8px 4px',
            textTransform: 'uppercase',
          }}
        >
          Session Archive ({conversations.length})
        </div>

        {conversations.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px 8px', color: '#64748b', fontSize: '13px' }}>
            No past sessions recorded.
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = conv.id === activeConversationId;
            return (
              <div
                key={conv.id}
                onClick={() => onSelectConversation(conv.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  margin: '4px 0',
                  borderRadius: '4px',
                  background: isActive ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                  border: isActive ? '1px solid var(--cyan-border)' : '1px solid transparent',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                  <div
                    style={{
                      fontSize: '13px',
                      color: isActive ? '#00f0ff' : '#cbd5e1',
                      fontWeight: isActive ? 600 : 400,
                    }}
                  >
                    {conv.title || 'Untitled Session'}
                  </div>
                  <div className="font-tech" style={{ fontSize: '10px', color: '#64748b' }}>
                    {new Date(conv.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                  title="Purge session"
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#64748b',
                    cursor: 'pointer',
                    padding: '4px',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  onMouseEnter={(e) => ((e.currentTarget as any).style.color = '#ef4444')}
                  onMouseLeave={(e) => ((e.currentTarget as any).style.color = '#64748b')}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Clear All Sessions Option */}
      {conversations.length > 1 && (
        <div style={{ padding: '4px 16px' }}>
          <button
            onClick={onClearAll}
            style={{
              background: 'none',
              border: 'none',
              color: '#ef4444',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            Clear All History
          </button>
        </div>
      )}

      {/* System Telemetry Module */}
      <div
        style={{
          padding: '12px 16px',
          borderTop: '1px solid rgba(0, 240, 255, 0.15)',
          background: 'rgba(5, 10, 22, 0.6)',
        }}
      >
        <div
          className="font-tech"
          style={{
            fontSize: '11px',
            color: '#38bdf8',
            letterSpacing: '1px',
            marginBottom: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>HOST TELEMETRY</span>
          <Activity className="w-3.5 h-3.5" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px' }}>
          <div
            style={{
              padding: '6px 8px',
              background: 'rgba(0, 0, 0, 0.3)',
              borderRadius: '4px',
              border: '1px solid rgba(255, 255, 255, 0.05)',
            }}
          >
            <div style={{ color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Cpu className="w-3 h-3 text-[#38bdf8]" />
              <span>CPU LOAD</span>
            </div>
            <div className="font-tech" style={{ color: '#f8fafc', fontWeight: 600, marginTop: '2px' }}>
              {systemStatus?.cpu_usage_percent !== undefined ? `${systemStatus.cpu_usage_percent}%` : '--'}
            </div>
          </div>

          <div
            style={{
              padding: '6px 8px',
              background: 'rgba(0, 0, 0, 0.3)',
              borderRadius: '4px',
              border: '1px solid rgba(255, 255, 255, 0.05)',
            }}
          >
            <div style={{ color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <HardDrive className="w-3 h-3 text-[#38bdf8]" />
              <span>RAM USAGE</span>
            </div>
            <div className="font-tech" style={{ color: '#f8fafc', fontWeight: 600, marginTop: '2px' }}>
              {systemStatus?.ram_percent !== undefined ? `${systemStatus.ram_percent}%` : '--'}
            </div>
          </div>
        </div>

        {/* Active Provider & Core Status Pill */}
        <div
          style={{
            marginTop: '8px',
            padding: '5px 8px',
            borderRadius: '4px',
            background: isGemini
              ? 'rgba(168, 85, 247, 0.12)'
              : (ollamaHealth?.connected ? 'rgba(0, 255, 170, 0.1)' : 'rgba(239, 68, 68, 0.1)'),
            border: `1px solid ${
              isGemini
                ? 'rgba(168, 85, 247, 0.4)'
                : (ollamaHealth?.connected ? 'rgba(0, 255, 170, 0.3)' : 'rgba(239, 68, 68, 0.3)')
            }`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
          }}
        >
          <span style={{ color: isGemini ? '#c084fc' : (ollamaHealth?.connected ? '#00ffaa' : '#ef4444'), fontWeight: 600 }}>
            {isGemini ? 'CORE: GEMINI [CLOUD]' : (ollamaHealth?.connected ? 'CORE: OLLAMA [LOCAL]' : 'OLLAMA: OFFLINE')}
          </span>
          <span style={{ color: isGemini ? '#e9d5ff' : '#00f0ff' }}>
            {activeModel || (isGemini ? 'gemini-1.5-flash' : (ollamaHealth?.models?.[0] || 'jarvis:latest'))}
          </span>
        </div>
      </div>

      {/* Footer Controls: Memories & Settings */}
      <div
        style={{
          padding: '12px 16px',
          borderTop: '1px solid rgba(0, 240, 255, 0.15)',
          display: 'flex',
          gap: '8px',
        }}
      >
        <button
          onClick={onOpenMemories}
          className="cyber-button"
          style={{ flex: 1, fontSize: '11px', padding: '6px 8px', justifyContent: 'center' }}
          title="Manage long term memories"
        >
          <Database className="w-3.5 h-3.5" />
          <span>Memories</span>
        </button>

        <button
          onClick={onOpenSettings}
          className="cyber-button"
          style={{ flex: 1, fontSize: '11px', padding: '6px 8px', justifyContent: 'center' }}
          title="System settings"
        >
          <Settings className="w-3.5 h-3.5" />
          <span>Settings</span>
        </button>
      </div>
    </aside>
  );
};
