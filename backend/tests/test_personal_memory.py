import pytest
import uuid
from backend.app.database.db import (
    add_memory,
    get_memories,
    get_memory,
    update_memory,
    delete_memory,
    search_memories,
    upsert_personal_memory,
    get_relevant_memories,
    delete_memory_by_query,
    set_setting,
    get_setting,
)
from backend.app.tools.system_tools import (
    save_memory_tool,
    update_memory_tool,
    delete_memory_tool,
    forget_memory_tool,
    search_memories_tool,
)
from backend.app.services.chat_service import chat_service
from backend.app.database.db import create_conversation

@pytest.fixture(autouse=True)
def clean_memory_state():
    """Ensure memory table is clean before and after tests."""
    from backend.app.database.db import get_db_connection
    conn = get_db_connection()
    conn.execute("DELETE FROM memories")
    conn.commit()
    conn.close()
    set_setting("memory_enabled", "true")
    yield
    conn = get_db_connection()
    conn.execute("DELETE FROM memories")
    conn.commit()
    conn.close()
    set_setting("memory_enabled", "true")

def test_upsert_memory_creates_and_updates():
    # 1. Initial creation
    res1 = upsert_personal_memory("User prefers concise answers", category="preference")
    assert res1["id"] is not None
    mems = get_memories()
    assert len(mems) == 1
    assert mems[0]["content"] == "User prefers concise answers"

    # 2. Conflicting update on same topic updates existing row
    res2 = upsert_personal_memory("User prefers detailed answers", category="preference")
    assert res2["id"] == res1["id"]
    mems2 = get_memories()
    assert len(mems2) == 1
    assert mems2[0]["content"] == "User prefers detailed answers"

def test_delete_memory_by_query():
    upsert_personal_memory("User favorite food is biryani", category="personal")
    upsert_personal_memory("User lives in Mumbai", category="personal")
    assert len(get_memories()) == 2

    deleted = delete_memory_by_query("food")
    assert deleted is not None
    assert "biryani" in deleted["content"]
    assert len(get_memories()) == 1

def test_get_relevant_memories_ranking():
    upsert_personal_memory("User prefers concise Python code", category="preference")
    upsert_personal_memory("User loves classical music", category="personal")
    upsert_personal_memory("User working on a fast FastAPI project", category="work")

    # Coding query should rank Python/FastAPI memories higher
    relevant = get_relevant_memories("How do I write Python async endpoints?", limit=2)
    assert len(relevant) == 2
    contents = [m["content"] for m in relevant]
    assert any("Python" in c for c in contents)

def test_save_memory_tool_respects_setting():
    set_setting("memory_enabled", "false")
    res = save_memory_tool("Remember I prefer dark chocolate")
    assert res["success"] is False
    assert "disabled" in res["error"].lower()
    assert len(get_memories()) == 0

    set_setting("memory_enabled", "true")
    res2 = save_memory_tool("Remember I prefer dark chocolate")
    assert res2["success"] is True
    assert len(get_memories()) == 1

@pytest.mark.asyncio
async def test_conversational_memory_end_to_end():
    c1 = create_conversation("Conversation 1")
    save_reply = ""
    async for chunk in chat_service.stream_chat(c1["id"], "Remember that I prefer concise answers"):
        if "content" in chunk and "chunk" in chunk:
            import json
            data = json.loads(chunk.replace("data: ", "").strip())
            save_reply += data.get("content", "")

    assert "Confirmed, Sir" in save_reply
    assert len(get_memories()) == 1

    # Verify across separate conversation
    c2 = create_conversation("Conversation 2")
    query_reply = ""
    async for chunk in chat_service.stream_chat(c2["id"], "What are my preferences?"):
        if "content" in chunk and "chunk" in chunk:
            import json
            data = json.loads(chunk.replace("data: ", "").strip())
            query_reply += data.get("content", "")

    assert "concise answers" in query_reply
