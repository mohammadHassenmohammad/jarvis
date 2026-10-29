"""
Regression tests for Strict Conversation Isolation.
Verifies that:
  1. Chat A contains a unique fact.
  2. Chat B asks about that fact.
  3. Chat B must not access Chat A's history or summary automatically.
  4. If that fact was explicitly saved as a permanent memory, Chat B may retrieve it when relevant.
  5. A summary update for Chat A must never change Chat B's summary.
  6. Deleting Chat A leaves Chat B and permanent memories intact.
"""

import pytest
import uuid
from backend.app.database.db import (
    create_conversation,
    add_message,
    get_messages,
    delete_conversation,
    upsert_personal_memory,
    get_relevant_memories,
    get_conversation_context,
    upsert_conversation_context,
    set_setting
)
from backend.app.services.context_service import context_service
from backend.app.services.chat_service import chat_service


def test_strict_conversation_isolation():
    """Verify Chat A's private facts do not leak into Chat B's context."""
    # Ensure memory is enabled
    set_setting("memory_enabled", "true")

    conv_a = create_conversation(title="Project Pegasus Architecture")
    cid_a = conv_a["id"]

    conv_b = create_conversation(title="Personal Finance Planning")
    cid_b = conv_b["id"]

    try:
        # Chat A has unique task-specific facts
        add_message(cid_a, role="user", content="Our server port is set to 9443 and the cluster name is Pegasus-Alpha.")
        add_message(cid_a, role="assistant", content="Acknowledged, Sir. Cluster Pegasus-Alpha configured on port 9443.")

        # Chat B is a fresh conversation
        add_message(cid_b, role="user", content="What port and cluster name are we using?")

        # Assemble context for Chat B
        prompt_b, msgs_b = context_service.assemble_context(
            conversation_id=cid_b,
            user_message="What port and cluster name are we using?",
            system_base_prompt="You are JARVIS."
        )

        # Chat B's context MUST NOT contain Chat A's private port or cluster name
        assert "9443" not in prompt_b, "Isolation violation: Chat A port leaked into Chat B prompt"
        assert "Pegasus-Alpha" not in prompt_b, "Isolation violation: Chat A cluster leaked into Chat B prompt"
        assert not any("9443" in m.get("content", "") for m in msgs_b), "Isolation violation in formatted messages"
        assert not any("Pegasus-Alpha" in m.get("content", "") for m in msgs_b), "Isolation violation in formatted messages"

    finally:
        delete_conversation(cid_a)
        delete_conversation(cid_b)


def test_permanent_memory_accessible_across_chats_when_relevant():
    """Verify an explicitly saved permanent memory is available to Chat B when relevant."""
    set_setting("memory_enabled", "true")

    conv_a = create_conversation(title="Setup Session")
    cid_a = conv_a["id"]

    conv_b = create_conversation(title="General Query")
    cid_b = conv_b["id"]

    unique_pref = f"User prefers dark mode syntax highlighting ({uuid.uuid4().hex[:6]})"
    try:
        # Explicitly save permanent memory from Chat A
        saved = upsert_personal_memory(content=unique_pref, category="preference", source_conversation_id=cid_a)
        assert saved["id"] is not None

        # Chat B asks about syntax highlighting preferences
        prompt_b, _ = context_service.assemble_context(
            conversation_id=cid_b,
            user_message="What are my syntax highlighting preferences?",
            system_base_prompt="You are JARVIS."
        )

        # Permanent memory should be retrieved in Chat B because it is explicitly relevant
        assert unique_pref in prompt_b, "Expected permanent memory to be retrieved in Chat B when relevant"

    finally:
        delete_conversation(cid_a)
        delete_conversation(cid_b)


def test_summary_update_for_chat_a_never_alters_chat_b_summary():
    """Verify rolling summaries are strictly scoped to their respective conversation IDs."""
    conv_a = create_conversation(title="Workflow A")
    cid_a = conv_a["id"]

    conv_b = create_conversation(title="Workflow B")
    cid_b = conv_b["id"]

    try:
        # Set distinct summaries for both chats
        upsert_conversation_context(
            conversation_id=cid_a,
            summary="Discussion about Rocket Propulsion Stage 1.",
            structured_facts=["Stage 1 thrust nominal"]
        )

        upsert_conversation_context(
            conversation_id=cid_b,
            summary="Review of Garden Irrigation Schedule.",
            structured_facts=["Irrigation at 06:00 AM"]
        )

        # Update Chat A's summary
        upsert_conversation_context(
            conversation_id=cid_a,
            summary="Updated: Rocket Propulsion Stage 1 and Stage 2 complete.",
            structured_facts=["Stage 1 and 2 complete"]
        )

        # Verify Chat B's summary is completely unaffected
        ctx_b = get_conversation_context(cid_b)
        assert ctx_b is not None
        assert ctx_b["summary"] == "Review of Garden Irrigation Schedule."
        assert "Rocket" not in ctx_b["summary"]
        assert ctx_b["structured_facts"] == ["Irrigation at 06:00 AM"]

    finally:
        delete_conversation(cid_a)
        delete_conversation(cid_b)


def test_deleting_conversation_preserves_permanent_memory():
    """Verify that deleting a chat never deletes permanent memories."""
    conv = create_conversation(title="Temporary Project")
    cid = conv["id"]

    permanent_fact = f"Permanent fact created in temporary chat {uuid.uuid4().hex[:6]}"
    saved = upsert_personal_memory(content=permanent_fact, category="personal", source_conversation_id=cid)

    # Delete the conversation
    delete_conversation(cid)

    # Verify conversation is gone
    msgs = get_messages(cid)
    assert len(msgs) == 0
    ctx = get_conversation_context(cid)
    assert ctx is None

    # Permanent memory MUST still exist
    relevant = get_relevant_memories(permanent_fact, limit=5)
    assert any(m["content"] == permanent_fact for m in relevant)
