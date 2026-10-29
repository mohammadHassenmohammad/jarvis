import React, { useState, useEffect } from 'react';
import type { Memory } from '../types';
import { X, Plus, Trash2, Edit2, Check, Database, Search, RotateCcw } from 'lucide-react';
import { api } from '../services/api';

interface MemoryManagerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MemoryManager: React.FC<MemoryManagerProps> = ({ isOpen, onClose }) => {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [newContent, setNewContent] = useState('');
  const [newCategory, setNewCategory] = useState('user_preference');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [editCategory, setEditCategory] = useState('user_preference');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadMemories();
    }
  }, [isOpen]);

  const loadMemories = async (query = searchQuery, category = filterCategory) => {
    setIsLoading(true);
    try {
      const data = await api.searchMemories(query, category);
      setMemories(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearchChange = (val: string) => {
    setSearchQuery(val);
    loadMemories(val, filterCategory);
  };

  const handleFilterChange = (cat: string) => {
    setFilterCategory(cat);
    loadMemories(searchQuery, cat);
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    try {
      const created = await api.createMemory(newContent.trim(), newCategory);
      setMemories([created, ...memories]);
      setNewContent('');
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteMemory(id);
      setMemories(memories.filter((m) => m.id !== id));
      if (editingId === id) setEditingId(null);
    } catch (e) {
      console.error(e);
    }
  };

  const handleStartEdit = (m: Memory) => {
    setEditingId(m.id);
    setEditContent(m.content);
    setEditCategory(m.category || 'user_preference');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditContent('');
  };

  const handleSaveEdit = async (id: string) => {
    if (!editContent.trim()) return;
    try {
      await api.updateMemory(id, editContent.trim(), editCategory);
      setMemories(
        memories.map((m) =>
          m.id === id ? { ...m, content: editContent.trim(), category: editCategory, updated_at: new Date().toISOString() } : m
        )
      );
      setEditingId(null);
    } catch (e) {
      console.error(e);
    }
  };

  if (!isOpen) return null;

  const categories = [
    { id: 'all', label: 'All Vault' },
    { id: 'user_preference', label: 'Preferences' },
    { id: 'work', label: 'Work & Code' },
    { id: 'personal', label: 'Personal' },
  ];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(3, 7, 18, 0.85)',
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
          width: '720px',
          maxWidth: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          background: 'rgba(9, 18, 38, 0.96)',
          border: '1px solid var(--cyan-glow)',
          boxShadow: '0 0 30px rgba(0, 240, 255, 0.25)',
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
            <Database className="w-5 h-5 text-[#00f0ff]" />
            <h2 className="font-hud" style={{ fontSize: '18px', color: '#00f0ff', letterSpacing: '1.5px' }}>
              LONG-TERM MEMORY VAULT
            </h2>
            <span
              style={{
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                color: '#38bdf8',
                background: 'rgba(0, 240, 255, 0.1)',
                padding: '2px 8px',
                borderRadius: '12px',
                border: '1px solid rgba(0, 240, 255, 0.2)',
              }}
            >
              {memories.length} RECORDS
            </span>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search & Category Filter Bar */}
        <div
          style={{
            padding: '12px 20px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            background: 'rgba(0, 0, 0, 0.2)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                position: 'relative',
                flex: 1,
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <Search
                className="w-4 h-4 text-[#94a3b8]"
                style={{ position: 'absolute', left: '10px', pointerEvents: 'none' }}
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                placeholder="Search memories by keyword..."
                style={{
                  width: '100%',
                  padding: '7px 12px 7px 32px',
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid var(--cyan-border)',
                  borderRadius: '4px',
                  color: '#f8fafc',
                  fontSize: '13px',
                  outline: 'none',
                }}
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => handleSearchChange('')}
                  style={{
                    position: 'absolute',
                    right: '10px',
                    background: 'none',
                    border: 'none',
                    color: '#94a3b8',
                    cursor: 'pointer',
                  }}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <button
              type="button"
              onClick={() => loadMemories(searchQuery, filterCategory)}
              className="cyber-button"
              style={{ padding: '6px 10px', fontSize: '12px' }}
              title="Refresh"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Filter Pills */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {categories.map((c) => {
              const active = filterCategory === c.id;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => handleFilterChange(c.id)}
                  style={{
                    padding: '3px 10px',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    borderRadius: '4px',
                    border: active ? '1px solid #00f0ff' : '1px solid rgba(255, 255, 255, 0.1)',
                    background: active ? 'rgba(0, 240, 255, 0.18)' : 'rgba(255, 255, 255, 0.04)',
                    color: active ? '#00f0ff' : '#94a3b8',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                >
                  {c.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Add Memory Form */}
        <form
          onSubmit={handleAdd}
          style={{
            padding: '14px 20px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            gap: '8px',
          }}
        >
          <input
            type="text"
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            placeholder="Record explicit memory (e.g., 'User prefers dark mode and concise summaries')..."
            style={{
              flex: 1,
              padding: '8px 12px',
              background: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid var(--cyan-border)',
              borderRadius: '4px',
              color: '#f8fafc',
              fontSize: '13px',
              outline: 'none',
            }}
          />
          <select
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
            style={{
              padding: '8px 10px',
              background: 'rgba(0, 0, 0, 0.5)',
              border: '1px solid var(--cyan-border)',
              borderRadius: '4px',
              color: '#38bdf8',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              outline: 'none',
            }}
          >
            <option value="user_preference">Preference</option>
            <option value="work">Work/Code</option>
            <option value="personal">Personal</option>
          </select>
          <button type="submit" className="cyber-button" style={{ padding: '8px 12px' }}>
            <Plus className="w-4 h-4" />
            <span>Store</span>
          </button>
        </form>

        {/* Memories List */}
        <div style={{ padding: '16px 20px', overflowY: 'auto', flex: 1 }}>
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#64748b', fontSize: '13px' }}>
              Scanning local memory vault...
            </div>
          ) : memories.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#64748b', fontSize: '13px' }}>
              {searchQuery || filterCategory !== 'all'
                ? 'No memories matched your search criteria.'
                : 'No memories saved yet. You can store custom preferences here or ask JARVIS to "Remember that..." in conversation.'}
            </div>
          ) : (
            memories.map((m) => (
              <div
                key={m.id}
                style={{
                  padding: '12px 14px',
                  margin: '8px 0',
                  borderRadius: '6px',
                  background: editingId === m.id ? 'rgba(0, 240, 255, 0.08)' : 'rgba(255, 255, 255, 0.03)',
                  border: editingId === m.id ? '1px solid #00f0ff' : '1px solid rgba(0, 240, 255, 0.2)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '12px',
                  transition: 'all 0.2s ease',
                }}
              >
                {editingId === m.id ? (
                  /* Edit Mode */
                  <div style={{ display: 'flex', flexDirection: 'column', flex: 1, gap: '8px' }}>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input
                        type="text"
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        placeholder="Memory content..."
                        style={{
                          flex: 1,
                          padding: '7px 10px',
                          background: 'rgba(0,0,0,0.6)',
                          border: '1px solid #00f0ff',
                          borderRadius: '4px',
                          color: '#fff',
                          fontSize: '13px',
                          outline: 'none',
                        }}
                        autoFocus
                      />
                      <select
                        value={editCategory}
                        onChange={(e) => setEditCategory(e.target.value)}
                        style={{
                          padding: '7px 8px',
                          background: 'rgba(0, 0, 0, 0.6)',
                          border: '1px solid #00f0ff',
                          borderRadius: '4px',
                          color: '#38bdf8',
                          fontSize: '12px',
                          fontFamily: 'var(--font-mono)',
                          outline: 'none',
                        }}
                      >
                        <option value="user_preference">Preference</option>
                        <option value="work">Work/Code</option>
                        <option value="personal">Personal</option>
                      </select>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        type="button"
                        onClick={() => handleSaveEdit(m.id)}
                        className="cyber-button"
                        style={{ padding: '4px 10px', fontSize: '12px' }}
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Save</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleCancelEdit}
                        style={{
                          padding: '4px 10px',
                          background: 'rgba(255, 255, 255, 0.05)',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                          borderRadius: '4px',
                          color: '#94a3b8',
                          cursor: 'pointer',
                          fontSize: '12px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <X className="w-3.5 h-3.5" />
                        <span>Cancel</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  /* View Mode */
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '5px' }}>
                      <span
                        style={{
                          fontSize: '10px',
                          fontFamily: 'var(--font-mono)',
                          padding: '2px 7px',
                          background: 'rgba(56, 189, 248, 0.15)',
                          border: '1px solid rgba(56, 189, 248, 0.4)',
                          borderRadius: '3px',
                          color: '#38bdf8',
                          textTransform: 'uppercase',
                        }}
                      >
                        {m.category.replace('_', ' ')}
                      </span>
                      <span style={{ fontSize: '11px', color: '#64748b' }}>
                        {m.created_at ? new Date(m.created_at).toLocaleDateString() : ''}
                      </span>
                    </div>
                    <div style={{ color: '#f1f5f9', fontSize: '14px', lineHeight: '1.4' }}>{m.content}</div>
                  </div>
                )}

                {/* Actions */}
                {editingId !== m.id && (
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                      onClick={() => handleStartEdit(m)}
                      title="Edit Memory"
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#94a3b8',
                        cursor: 'pointer',
                        padding: '4px',
                        transition: 'color 0.2s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = '#00f0ff')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDelete(m.id)}
                      title="Delete Memory"
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#ef4444',
                        cursor: 'pointer',
                        padding: '4px',
                        transition: 'opacity 0.2s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.7')}
                      onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
