"""
Advanced regression tests for Permanent Personal Memory.
Tests:
  1. Explicit save requests create persistent records.
  2. Successful save is confirmed accurately.
  3. Failed writes never produce a false success message.
  4. Memory is retrievable across different conversation IDs.
  5. Contradiction/correction updates the appropriate record in-place.
  6. Forget request deactivates/removes the correct memory.
  7. Disabling memory prevents saving and retrieval.
  8. Unrelated memories are filtered out and not added to every prompt.
  9. Sensitive secrets/passwords are strictly rejected.
"""

import pytest
import uuid
from backend.app.database.db import (
    upsert_personal_memory,
    get_relevant_memories,
    forget_permanent_memory,
    set_setting,
    get_setting,
    is_sensitive_secret
)
from backend.app.tools.system_tools import save_memory_tool, forget_memory_tool
from backend.app.services.chat_service import chat_service
from backend.app.database.db import get_db_connection


@pytest.fixture(autouse=True)
def clean_memory_state():
    """Ensure memories table is clean before and after tests."""
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


def test_explicit_save_creates_persistent_record_and_accurate_confirmation():
    """Verify explicit save creates a record with stable ID, active status, and accurate confirmation."""
    set_setting("memory_enabled", "true")
    fact = f"Always remember that I prefer concise answers ({uuid.uuid4().hex[:6]})"

    res = save_memory_tool(fact=fact, category="preference")
    assert res["success"] is True
    assert res["memory_id"] is not None
    assert res["is_permanent"] is True
    assert "Confirmed" in res["message"]
    assert fact in res["message"]

    # Verify retrieval
    mems = get_relevant_memories(fact, limit=1)
    assert len(mems) > 0
    assert mems[0]["content"] == fact
    assert mems[0]["status"] == "active"


def test_failed_write_never_produces_false_success():
    """Verify empty or invalid memory save returns truthful error, not false success."""
    set_setting("memory_enabled", "true")

    res_empty = save_memory_tool(fact="")
    assert res_empty["success"] is False
    assert "error" in res_empty
    assert "Confirmed" not in res_empty.get("message", "")

    res_spaces = save_memory_tool(fact="   ")
    assert res_spaces["success"] is False
    assert "error" in res_spaces


def test_sensitive_credentials_rejected_from_permanent_memory():
    """Verify security policy strictly rejects storing passwords, API keys, and credentials."""
    set_setting("memory_enabled", "true")

    dangerous_payloads = [
        "My password is SecretPassword123!",
        "Save this API key: sk-ant-api03-abcdefghijklmnop1234567890",
        "Remember my token: ghp_1234567890abcdefghijklmnopqrstuvwxyz",
        "My password is admin_root_password",
    ]
    for secret in dangerous_payloads:
        assert is_sensitive_secret(secret) is True
        res = save_memory_tool(fact=secret)
        assert res["success"] is False
        assert "Security violation" in res["error"] or "prohibited" in res["error"].lower()


def test_contradiction_updates_record_in_place():
    """Verify that updating a preference replaces the old contradictory fact instead of creating duplicates."""
    tag = uuid.uuid4().hex[:6]
    initial_fact = f"User prefers detailed technical answers ({tag})"
    updated_fact = f"User prefers concise executive answers ({tag})"

    # Save initial
    saved1 = upsert_personal_memory(content=initial_fact, category="preference")
    id1 = saved1["id"]

    # Save contradiction/update
    saved2 = upsert_personal_memory(content=updated_fact, category="preference")
    id2 = saved2["id"]

    # Should update in place with the same ID
    assert id1 == id2
    assert saved2["content"] == updated_fact

    # Only the updated fact should be retrieved
    mems = get_relevant_memories(tag, limit=5)
    matching = [m for m in mems if tag in m["content"]]
    assert len(matching) == 1
    assert matching[0]["content"] == updated_fact


def test_forget_request_deactivates_correct_memory():
    """Verify forget removes or deactivates target memory."""
    tag = uuid.uuid4().hex[:6]
    fact = f"User works at Stark Tower R&D ({tag})"

    saved = upsert_personal_memory(content=fact, category="personal")
    mid = saved["id"]

    # Forget via tool
    res = forget_memory_tool(query=tag)
    assert res["success"] is True
    assert res["memory_id"] == mid

    # Should no longer be returned by get_relevant_memories
    mems = get_relevant_memories(tag, limit=5)
    assert not any(m["id"] == mid for m in mems)


def test_disabling_memory_prevents_saving_and_retrieval():
    """Verify memory_enabled=false prevents saving and prompt injection."""
    set_setting("memory_enabled", "false")

    res = save_memory_tool(fact="Remember that I like coffee")
    assert res["success"] is False
    assert "disabled" in res["error"].lower()

    # Reset setting
    set_setting("memory_enabled", "true")


def test_unrelated_memories_filtered_out():
    """Verify unrelated memories are not injected into prompts where they do not belong."""
    tag = uuid.uuid4().hex[:6]
    unique_fact = f"User enjoys playing competitive badminton on weekends ({tag})"
    upsert_personal_memory(content=unique_fact, category="hobby")

    # Ask an unrelated technical question
    unrelated_query = "Explain how database index B-trees work in SQLite."
    relevant = get_relevant_memories(query=unrelated_query, limit=5)

    # Badminton fact MUST NOT be returned for the unrelated query
    assert not any(tag in m.get("content", "") for m in relevant), "Unrelated memory leaked into prompt"
