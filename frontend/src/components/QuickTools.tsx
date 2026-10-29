import React from 'react';
import { Clock, Activity, FileText, Calculator, Folder, Search, Globe } from 'lucide-react';

interface QuickToolsProps {
  onQuickCommand: (prompt: string) => void;
  isLoading: boolean;
}

export const QuickTools: React.FC<QuickToolsProps> = ({ onQuickCommand, isLoading }) => {
  const tools = [
    { label: 'Time & Date', prompt: 'what time is it?', icon: <Clock className="w-3.5 h-3.5" /> },
    { label: 'Diagnostics', prompt: 'system diagnostics', icon: <Activity className="w-3.5 h-3.5" /> },
    { label: 'YouTube', prompt: 'open youtube', icon: <Globe className="w-3.5 h-3.5 text-red-400" /> },
    { label: 'Google', prompt: 'open google', icon: <Globe className="w-3.5 h-3.5 text-blue-400" /> },
    { label: 'Notepad', prompt: 'open notepad', icon: <FileText className="w-3.5 h-3.5" /> },
    { label: 'Calculator', prompt: 'open calculator', icon: <Calculator className="w-3.5 h-3.5" /> },
    { label: 'Downloads', prompt: 'open downloads', icon: <Folder className="w-3.5 h-3.5" /> },
    { label: 'Search Web', prompt: 'search web for latest AI news', icon: <Search className="w-3.5 h-3.5" /> },
  ];

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        overflowX: 'auto',
        padding: '6px 0',
        scrollbarWidth: 'none',
      }}
    >
      <span className="font-tech" style={{ fontSize: '11px', color: '#64748b', whiteSpace: 'nowrap', marginRight: '4px' }}>
        DIRECT PROTOCOLS:
      </span>
      {tools.map((t) => (
        <button
          key={t.label}
          onClick={() => onQuickCommand(t.prompt)}
          disabled={isLoading}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '5px 12px',
            background: 'rgba(0, 240, 255, 0.06)',
            border: '1px solid rgba(0, 240, 255, 0.25)',
            borderRadius: '4px',
            color: '#cbd5e1',
            fontSize: '12px',
            fontFamily: 'var(--font-mono)',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            whiteSpace: 'nowrap',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => {
            if (!isLoading) {
              (e.currentTarget as any).style.borderColor = '#00f0ff';
              (e.currentTarget as any).style.color = '#00f0ff';
              (e.currentTarget as any).style.background = 'rgba(0, 240, 255, 0.18)';
              (e.currentTarget as any).style.boxShadow = '0 0 10px rgba(0, 240, 255, 0.3)';
              (e.currentTarget as any).style.transform = 'translateY(-1px)';
            }
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as any).style.borderColor = 'rgba(0, 240, 255, 0.25)';
            (e.currentTarget as any).style.color = '#cbd5e1';
            (e.currentTarget as any).style.background = 'rgba(0, 240, 255, 0.06)';
            (e.currentTarget as any).style.boxShadow = 'none';
            (e.currentTarget as any).style.transform = 'none';
          }}
          onMouseDown={(e) => {
            if (!isLoading) (e.currentTarget as any).style.transform = 'scale(0.96)';
          }}
          onMouseUp={(e) => {
            if (!isLoading) (e.currentTarget as any).style.transform = 'translateY(-1px)';
          }}
        >
          {t.icon}
          <span>{t.label}</span>
        </button>
      ))}
    </div>
  );
};
