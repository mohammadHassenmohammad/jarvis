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
            source_conversation_id TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            is_permanent INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Safe migration for existing memories tables
    cursor.execute("PRAGMA table_info(memories)")
    mem_cols = {row["name"] for row in cursor.fetchall()}
    if "source_conversation_id" not in mem_cols:
        cursor.execute("ALTER TABLE memories ADD COLUMN source_conversation_id TEXT")
    if "status" not in mem_cols:
        cursor.execute("ALTER TABLE memories ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    if "is_permanent" not in mem_cols:
        cursor.execute("ALTER TABLE memories ADD COLUMN is_permanent INTEGER NOT NULL DEFAULT 1")

    # Conversation Context & Rolling Summary table (strict isolation per conversation_id)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_context (
            conversation_id TEXT PRIMARY KEY,
            summary TEXT NOT NULL DEFAULT '',
            structured_facts TEXT NOT NULL DEFAULT '[]',
            last_summarized_message_id TEXT,
            message_count_at_summary INTEGER DEFAULT 0,
            version INTEGER DEFAULT 1,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)

    # Performance and isolation indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv_created ON messages(conversation_id, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_status_cat ON memories(status, category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_context_updated ON conversation_context(updated_at)")

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
    cursor.execute("DELETE FROM conversation_context WHERE conversation_id = ?", (conversation_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def clear_all_conversations() -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    cursor.execute("DELETE FROM conversation_context")
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

def get_memories(include_deleted: bool = False) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if include_deleted:
        cursor.execute("SELECT * FROM memories ORDER BY created_at DESC")
    else:
        cursor.execute("SELECT * FROM memories WHERE status = 'active' ORDER BY created_at DESC")
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

FORBIDDEN_SECRET_PATTERNS = [
    r"\b(?:password|passwd|pwd)\s*(?:is|:|=)\s*\S+",
    r"\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|bearer)\s*(?:is|:|=)\s*\S+",
    r"\b(?:sk-[a-zA-Z0-9_-]{20,})\b",
    r"\b(?:ghp_[a-zA-Z0-9]{20,})\b",
    r"\b(?:-----BEGIN\s+(?:RSA|OPENSSH|DSA|EC|PGP)?\s*PRIVATE\s+KEY-----)",
]

def is_sensitive_secret(content: str) -> bool:
    """Detects credentials, tokens, passwords, and private keys to prevent storing secrets in memory."""
    import re
    lower = content.lower()
    for pat in FORBIDDEN_SECRET_PATTERNS:
        if re.search(pat, content, re.IGNORECASE):
            return True
    if any(k in lower for k in ["my password is", "my api key is", "my secret token is", "private key:"]):
        return True
    return False

def upsert_personal_memory(
    content: str,
    category: str = "preference",
    source_conversation_id: Optional[str] = None
) -> dict[str, Any]:
    """
    Saves or updates a permanent personal memory entry.
    Validates meaningful content, strictly rejects passwords/credentials,
    and updates existing memories on the same topic in place to avoid contradiction.
    """
    import re
    clean_content = content.strip()
    if not clean_content:
        raise ValueError("Memory content cannot be empty.")
    if is_sensitive_secret(clean_content):
        raise ValueError("Security violation: Credentials, passwords, or authentication secrets must never be stored in personal memory.")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Extract significant content terms (3+ chars)
    words = [w for w in re.findall(r'[a-zA-Z0-9]+', clean_content.lower()) if len(w) >= 3 and w not in {"the", "and", "that", "user", "prefer", "prefers", "likes", "preferring", "permanent", "remember"}]
    
    cursor.execute("SELECT * FROM memories WHERE category = ? AND status = 'active'", (category,))
    existing_rows = [dict(r) for r in cursor.fetchall()]
    
    target_id = None
    best_score = 0
    for row in existing_rows:
        row_content_lower = row["content"].lower()
        shared_keywords = sum(1 for w in words if w in row_content_lower)
        if ("name is" in clean_content.lower() and "name is" in row_content_lower):
            target_id = row["id"]
            break
        threshold = max(2, len(words) // 2) if len(words) >= 4 else 1
        if len(words) > 0 and shared_keywords >= threshold and shared_keywords > best_score:
            best_score = shared_keywords
            target_id = row["id"]

    now = datetime.now().isoformat()
    if target_id:
        cursor.execute(
            """
            UPDATE memories 
            SET content = ?, category = ?, updated_at = ?, source_conversation_id = COALESCE(?, source_conversation_id), status = 'active', is_permanent = 1
            WHERE id = ?
            """,
            (clean_content, category, now, source_conversation_id, target_id)
        )
        mid = target_id
    else:
        mid = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO memories (id, category, content, created_at, updated_at, source_conversation_id, status, is_permanent)
            VALUES (?, ?, ?, ?, ?, ?, 'active', 1)
            """,
            (mid, category, clean_content, now, now, source_conversation_id)
        )
    conn.commit()
    conn.close()
    return {
        "id": mid,
        "category": category,
        "content": clean_content,
        "source_conversation_id": source_conversation_id,
        "status": "active",
        "is_permanent": 1,
        "updated_at": now
    }

def get_relevant_memories(query: str = "", limit: int = 5) -> list[dict[str, Any]]:
    """
    Retrieves active permanent memories with relevance filtering for prompt injection.
    Filters out completely unrelated memories so prompts are not polluted with irrelevant facts.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories WHERE status = 'active' ORDER BY updated_at DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return []

    if not query or not query.strip():
        # Without a query, return top active preferences/personal facts
        return [r for r in rows if r.get("category") in ("preference", "personal")][:limit]

    import re
    query_tokens = [t for t in re.findall(r'[a-zA-Z0-9]+', query.lower()) if len(t) >= 3 and t not in {"the", "and", "what", "are", "tell", "show", "how", "why"}]
    TECH_WORDS = {"python", "fastapi", "code", "async", "endpoints", "endpoint", "api", "project", "work", "database", "sql", "backend", "programming"}
    query_is_tech = any(t in TECH_WORDS for t in query_tokens)

    scored_memories = []
    for m in rows:
        cat = (m.get("category") or "").lower()
        c_lower = m["content"].lower()
        
        shared_hits = sum(1 for t in query_tokens if t in c_lower)
        
        # Determine relevance:
        # 1. Direct keyword match
        # 2. General user preference on formatting/style (e.g. 'concise answers', 'detailed answers')
        # 3. Work/technical context match when query is technical
        is_formatting_pref = "preference" in cat and any(w in c_lower for w in ["concise", "detailed", "brief", "polite", "style", "answer"])
        is_tech_relevant = query_is_tech and (cat == "work" or any(tw in c_lower for tw in TECH_WORDS))
        
        if shared_hits > 0 or is_formatting_pref or is_tech_relevant:
            score = shared_hits * 5.0
            if "preference" in cat:
                score += 3.0
            if is_formatting_pref:
                score += 2.0
            if is_tech_relevant:
                score += 2.5
            scored_memories.append((score, m))

    scored_memories.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_memories[:limit]]

def delete_memory_by_query(query: str) -> Optional[dict[str, Any]]:
    """
    Deactivates/deletes the memory entry most closely matching the search query.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    mems = get_memories()
    q_words = [w for w in query.lower().split() if len(w) > 2]
    target = None
    for m in mems:
        if any(w in m["content"].lower() for w in q_words):
            target = m
            break
    if target:
        cursor.execute("DELETE FROM memories WHERE id = ?", (target["id"],))
        conn.commit()
    conn.close()
    return target

def forget_permanent_memory(query: str = "", memory_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    """
    Deactivates a permanent memory entry by setting status to 'deleted'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    target = None

    if memory_id:
        cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        if row:
            target = dict(row)
            cursor.execute("UPDATE memories SET status = 'deleted', updated_at = ? WHERE id = ?", (now, memory_id))
    elif query and query.strip():
        results = search_memories(query=query, limit=5)
        active_results = [r for r in results if r.get("status", "active") == "active"]
        if active_results:
            target = active_results[0]
            cursor.execute("UPDATE memories SET status = 'deleted', updated_at = ? WHERE id = ?", (now, target["id"]))
        else:
            all_m = get_memories()
            q_words = [w for w in query.lower().split() if len(w) > 2]
            for m in all_m:
                if m.get("status", "active") == "active" and any(w in m["content"].lower() for w in q_words):
                    target = m
                    cursor.execute("UPDATE memories SET status = 'deleted', updated_at = ? WHERE id = ?", (now, m["id"]))
                    break

    conn.commit()
    conn.close()
    return target

# Conversation Context & Rolling Summary Operations
def get_conversation_context(conversation_id: str) -> Optional[dict[str, Any]]:
    """Retrieves conversation-specific rolling summary and structured facts."""
    if not conversation_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversation_context WHERE conversation_id = ?", (conversation_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if d.get("structured_facts"):
        try:
            d["structured_facts"] = json.loads(d["structured_facts"])
        except Exception:
            d["structured_facts"] = []
    return d

def upsert_conversation_context(
    conversation_id: str,
    summary: str,
    structured_facts: Optional[list[str]] = None,
    last_summarized_message_id: Optional[str] = None,
    message_count_at_summary: int = 0
) -> dict[str, Any]:
    """Saves or updates conversation-specific rolling summary and structured facts."""
    if not conversation_id:
        raise ValueError("conversation_id cannot be empty.")
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    facts_json = json.dumps(structured_facts or [])
    cursor.execute(
        """
        INSERT INTO conversation_context (conversation_id, summary, structured_facts, last_summarized_message_id, message_count_at_summary, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            summary = excluded.summary,
            structured_facts = excluded.structured_facts,
            last_summarized_message_id = excluded.last_summarized_message_id,
            message_count_at_summary = excluded.message_count_at_summary,
            version = conversation_context.version + 1,
            updated_at = excluded.updated_at
        """,
        (conversation_id, summary, facts_json, last_summarized_message_id, message_count_at_summary, now)
    )
    conn.commit()
    conn.close()
    return {
        "conversation_id": conversation_id,
        "summary": summary,
        "structured_facts": structured_facts or [],
        "last_summarized_message_id": last_summarized_message_id,
        "message_count_at_summary": message_count_at_summary,
        "updated_at": now
    }

def search_conversation_messages(
    conversation_id: str,
    query: str,
    limit: int = 5
) -> list[dict[str, Any]]:
    """
    Layer D: Search older original messages strictly within the active conversation.
    Enforces strict conversation isolation boundary: NEVER queries other conversation IDs.
    """
    if not conversation_id or not query or not query.strip():
        return []
    
    import re
    tokens = [t for t in re.findall(r'[a-zA-Z0-9_\-\.]+', query.lower()) if len(t) >= 2]
    if not tokens:
        return []

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, conversation_id, role, content, created_at FROM messages WHERE conversation_id = ? AND role IN ('user', 'assistant') ORDER BY created_at ASC",
        (conversation_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    scored = []
    clean_q = query.lower().strip()
    for r in rows:
        c_lower = r["content"].lower()
        score = 0.0
        if clean_q in c_lower:
            score += 15.0
        for t in tokens:
            if t in c_lower:
                score += 3.0
        if score > 0:
            r["score"] = score
            scored.append(r)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]

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
