import pytest
from backend.app.database.db import (
    init_db,
    create_conversation,
    get_conversations,
    get_conversation,
    delete_conversation,
    add_message,
    get_messages,
    add_memory,
    get_memories,
    delete_memory,
    get_setting,
    set_setting
)

def test_database_lifecycle():
    init_db()
    
    # 1. Test conversation
    conv = create_conversation(title="Test Diagnostic Session")
    assert conv["id"] is not None
    assert conv["title"] == "Test Diagnostic Session"
    
    retrieved = get_conversation(conv["id"])
    assert retrieved is not None
    assert retrieved["title"] == "Test Diagnostic Session"
    
    # 2. Test messages
    msg1 = add_message(conv["id"], role="user", content="Good morning, Jarvis.")
    msg2 = add_message(conv["id"], role="assistant", content="Good morning, Sir.")
    assert msg1["content"] == "Good morning, Jarvis."
    
    msgs = get_messages(conv["id"])
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    
    # 3. Test memory
    mem = add_memory("User prefers dark mode and concise summaries", category="user_preference")
    assert mem["id"] is not None
    all_mems = get_memories()
    assert any(m["id"] == mem["id"] for m in all_mems)
    
    # 4. Test delete memory
    del_ok = delete_memory(mem["id"])
    assert del_ok is True
    
    # 5. Test settings
    set_setting("diagnostic_mode", "active")
    val = get_setting("diagnostic_mode")
    assert val == "active"
    
    # 6. Test delete conversation
    del_conv = delete_conversation(conv["id"])
    assert del_conv is True
    assert get_conversation(conv["id"]) is None
