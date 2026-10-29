import sqlite3
import json
import uuid
from datetime import datetime
from typing import Any, Optional
from ..config import settings

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tool_calls TEXT,
            tool_results TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)
    
    # Memories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL DEFAULT 'general',
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Key-value Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    # Default settings if not already present
    default_settings = {
        "model": settings.DEFAULT_MODEL,
        "provider": settings.DEFAULT_PROVIDER,
        "system_prompt": settings.JARVIS_SYSTEM_PROMPT,
        "memory_enabled": "true",
        "voice_auto_speak": "true",
        "speech_rate": "1.0",
        "speech_pitch": "1.0",
        "voice_input_mode": "click",
        "wake_word_enabled": "true",
        "wake_word": "jarvis",
        "preferred_voice": "",
        "voice_language": "en-IN",
        "vad_silence_timeout": "1.4",
        "voice_feedback": "true",
        "max_recording_duration": "30",
        "interrupt_on_wake": "true",
        "continuous_mode": "true",
        "whisper_backend_enabled": "true",
        "n8n_enabled": "true" if settings.N8N_ENABLED else "false",
        "n8n_webhook_url": settings.N8N_WEBHOOK_URL,
        "n8n_auth_token": settings.N8N_AUTH_TOKEN,
        "retrieval_enabled": "true" if settings.RETRIEVAL_ENABLED else "false",
        "retrieval_limit": str(settings.RETRIEVAL_MAX_SNIPPETS),
        "gemini_api_key": settings.GEMINI_API_KEY,
        "gemini_model": settings.GEMINI_DEFAULT_MODEL,
    }
    
    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)", (k, v))
        
    conn.commit()
    conn.close()

# Conversation Operations
def create_conversation(title: str = "New Session") -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cid = str(uuid.uuid4())
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (cid, title, now, now)
    )
    conn.commit()
    conn.close()
    return {"id": cid, "title": title, "created_at": now, "updated_at": now}

def get_conversations() -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_conversation(conversation_id: str) -> Optional[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_conversation(conversation_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def clear_all_conversations() -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    cursor.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()
    return True

def update_conversation_title(conversation_id: str, title: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute(
        "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
        (title, now, conversation_id)
    )
    conn.commit()
    conn.close()

# Message Operations
def add_message(
    conversation_id: str,
    role: str,
    content: str,
    tool_calls: Optional[list] = None,
    tool_results: Optional[list] = None
) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    mid = str(uuid.uuid4())
    now = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO messages (id, conversation_id, role, content, tool_calls, tool_results, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mid,
            conversation_id,
            role,
            content,
            json.dumps(tool_calls) if tool_calls else None,
            json.dumps(tool_results) if tool_results else None,
            now
        )
    )
    # Also update conversation timestamp
    cursor.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
    conn.commit()
    conn.close()
    return {
        "id": mid,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "created_at": now
    }

def get_messages(conversation_id: str) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    messages = []
    for row in rows:
        d = dict(row)
        if d.get("tool_calls"):
            try:
                d["tool_calls"] = json.loads(d["tool_calls"])
            except Exception:
                pass
        if d.get("tool_results"):
            try:
                d["tool_results"] = json.loads(d["tool_results"])
            except Exception:
                pass
        messages.append(d)
    return messages

# Memory Operations
def add_memory(content: str, category: str = "general") -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    mid = str(uuid.uuid4())
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO memories (id, category, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (mid, category, content, now, now)
    )
    conn.commit()
    conn.close()
    return {"id": mid, "category": category, "content": content, "created_at": now, "updated_at": now}

def get_memories() -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_memory(memory_id: str) -> Optional[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def search_memories(
    query: str = "",
    category: Optional[str] = None,
    limit: int = 50
) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = "SELECT * FROM memories WHERE 1=1"
    params: list[Any] = []
    
    if category and category.strip() and category != "all":
        sql += " AND category = ?"
        params.append(category.strip())
        
    if query and query.strip():
        sql += " AND content LIKE ?"
        params.append(f"%{query.strip()}%")
        
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(sql, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_memory(memory_id: str, content: str, category: Optional[str] = None) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    if category:
        cursor.execute(
            "UPDATE memories SET content = ?, category = ?, updated_at = ? WHERE id = ?",
            (content, category, now, memory_id)
        )
    else:
        cursor.execute(
            "UPDATE memories SET content = ?, updated_at = ? WHERE id = ?",
            (content, now, memory_id)
        )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def delete_memory(memory_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def search_relevant_conversations(
    query: str,
    exclude_conversation_id: Optional[str] = None,
    limit: int = 4
) -> list[dict[str, Any]]:
    """
    Local privacy-preserving retrieval of past conversation messages relevant to query.
    Extracts terms, searches SQLite messages & conversations, ranks results by relevance & recency.
    """
    import re
    if not query or not query.strip():
        return []
        
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when",
        "where", "who", "did", "do", "does", "we", "i", "you", "my", "your", "me",
        "to", "in", "for", "on", "with", "at", "by", "from", "up", "about", "into",
        "over", "after", "can", "could", "would", "should", "tell", "show", "give",
        "please", "sir", "jarvis", "that", "this", "it", "and", "or", "of", "be"
    }
    raw_tokens = re.findall(r'[a-zA-Z0-9_\-\.]+', query.lower())
    terms = [t for t in raw_tokens if len(t) >= 2 and t not in stopwords]
    
    if not terms:
        terms = [t for t in raw_tokens if len(t) > 1]
    if not terms:
        return []

    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = """
        SELECT m.id, m.conversation_id, m.role, m.content, m.created_at, c.title as conversation_title
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        WHERE m.role IN ('user', 'assistant')
    """
    params: list[Any] = []
    if exclude_conversation_id:
        sql += " AND m.conversation_id != ?"
        params.append(exclude_conversation_id)
        
    cursor.execute(sql, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    
    clean_query = query.lower().strip()
    scored_results: list[dict[str, Any]] = []
    
    for row in rows:
        d = dict(row)
        content_lower = d["content"].lower()
        title_lower = (d["conversation_title"] or "").lower()
        
        score = 0.0
        # Exact phrase match bonus
        if clean_query in content_lower:
            score += 15.0
        if clean_query in title_lower:
            score += 10.0
            
        # Keyword term hits
        for term in terms:
            if term in content_lower:
                score += 3.0 + min(content_lower.count(term), 3) * 0.5
            if term in title_lower:
                score += 4.0
                
        if score > 0:
            d["relevance_score"] = round(score, 2)
            scored_results.append(d)
            
    scored_results.sort(key=lambda x: (x["relevance_score"], x["created_at"]), reverse=True)
    return scored_results[:limit]

# Settings Operations
def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def get_all_settings() -> dict[str, str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM system_settings")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def set_setting(key: str, value: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO system_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()
