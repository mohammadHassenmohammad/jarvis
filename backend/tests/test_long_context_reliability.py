"""
Long-Conversation Context & Reliability Tests.
Verifies:
  1. Early critical fact at turn 2 survives across 100+ turns and is retrieved via Layer B rolling summary and Layer D message search.
  2. Corrections update structured facts and rolling summary, overriding outdated facts.
  3. Context budget limits are strictly adhered to (< 4000 tokens).
  4. Unrelated historical topics (e.g. car preferences) do not pollute unrelated conversations or topics.
"""

import pytest
import uuid
from backend.app.database.db import (
    create_conversation,
    delete_conversation,
    add_message,
    get_messages,
    get_conversation_context,
    search_conversation_messages,
)
from backend.app.services.context_service import context_service


def test_long_conversation_early_fact_retrieval_and_budget():
    """
    Test long-conversation behavior across 100+ messages:
    1. Early critical fact at turn 2.
    2. Over 100 intervening messages on unrelated topics.
    3. Rolling summary & structured facts capture the conversation purpose and key facts.
    4. Exact older message search (Layer D) retrieves the specific early statement.
    5. Assembled prompt strictly honors the token budget (< 4000 tokens).
    """
    conv = create_conversation("Long Context Test")
    conv_id = conv["id"]

    try:
        # Turn 1: Initial user setup
        add_message(conv_id, "user", "Let's architect a secure data storage system.")
        add_message(conv_id, "assistant", "Certainly, sir. What encryption standards and parameters shall we adopt?")

        # Turn 2: Critical early fact
        critical_fact = "The master storage encryption standard must strictly use ChaCha20-Poly1305 with 256-bit key rotation."
        add_message(conv_id, "user", critical_fact)
        add_message(conv_id, "assistant", "Noted, sir. I have registered ChaCha20-Poly1305 with 256-bit key rotation as the master storage encryption standard.")

        # Generate 100+ messages on other technical topics to push early messages far outside Layer A recent window
        topics = [
            "file indexing algorithms",
            "cache eviction policies",
            "TCP socket timeouts",
            "buffer pool allocations",
            "thread concurrency limits",
            "log rotation intervals",
            "heartbeat monitoring",
            "disk I/O throttling",
            "JSON serialization speed",
            "memory leak profiling",
        ]

        for i in range(1, 105):
            topic = topics[i % len(topics)]
            add_message(conv_id, "user", f"Step {i}: Please configure the parameters for {topic}.")
            add_message(conv_id, "assistant", f"Step {i} completed. The parameters for {topic} have been tuned and verified.")

        # Verify total messages exceed 100
        all_msgs = get_messages(conv_id)
        assert len(all_msgs) >= 110, f"Expected > 110 messages, got {len(all_msgs)}"

        # Layer A (recent window) should NOT contain the early critical fact
        recent_msgs = all_msgs[-8:]
        assert not any("ChaCha20-Poly1305" in m["content"] for m in recent_msgs)

        # 1. Test Layer D: Direct conversation-scoped search can retrieve the original statement
        search_results = search_conversation_messages(conv_id, "ChaCha20-Poly1305 encryption")
        assert len(search_results) > 0
        assert any("ChaCha20-Poly1305" in r["content"] for r in search_results)
        # Ensure it only returned results from this conversation
        assert all(r["conversation_id"] == conv_id for r in search_results)

        # 2. Update rolling summary and structured facts (Layer B & C)
        context_service.update_conversation_summary(
            conv_id,
            new_summary="Designing secure data storage system. Established core crypto parameters and tuned subcomponents.",
            key_facts=["Master storage encryption: ChaCha20-Poly1305 with 256-bit key rotation"],
            decisions=["Adopted ChaCha20-Poly1305 for primary storage volume"],
            user_corrections=[]
        )

        ctx_row = get_conversation_context(conv_id)
        assert ctx_row is not None
        assert any("ChaCha20-Poly1305" in f for f in ctx_row["structured_facts"])

        # 3. Test assemble_context when user asks about the early encryption standard
        system_prompt, formatted_messages = context_service.assemble_context(
            conversation_id=conv_id,
            user_message="What encryption standard did we decide on for our master storage?"
        )

        full_prompt_text = system_prompt + " " + " ".join([m["content"] for m in formatted_messages])
        assert "ChaCha20-Poly1305" in full_prompt_text, "Assembled prompt must include the early critical fact from summary/Layer D"

        # Context budget verification: Total estimated tokens must stay safely within limit
        total_tokens = len(system_prompt.split()) + sum(len(m["content"].split()) for m in formatted_messages)
        assert total_tokens <= 4000
        assert total_tokens > 0

    finally:
        delete_conversation(conv_id)


def test_corrections_override_outdated_summary_content():
    """
    Test that later user corrections properly update structured facts and rolling summary,
    and override outdated information.
    """
    conv = create_conversation("Correction Test")
    conv_id = conv["id"]

    try:
        # Initial decision
        add_message(conv_id, "user", "Set the database replica count to 3.")
        add_message(conv_id, "assistant", "Replica count set to 3.")

        context_service.update_conversation_summary(
            conv_id,
            new_summary="Configuring database cluster.",
            key_facts=["Replica count: 3"],
            decisions=["Replica count set to 3"],
            user_corrections=[]
        )

        # User issues a correction
        correction_msg = "Actually, correction: do not use 3 replicas, change the replica count to 5 due to high availability needs."
        add_message(conv_id, "user", correction_msg)
        add_message(conv_id, "assistant", "Understood, sir. Corrected replica count to 5.")

        # Incremental update with correction
        context_service.update_conversation_summary(
            conv_id,
            new_summary="Configuring database cluster. Corrected replica count to 5.",
            key_facts=["Replica count: 5 (overrides previous value of 3)"],
            decisions=["Replica count set to 5"],
            user_corrections=["Replica count is 5, not 3"]
        )

        # Retrieve context
        ctx_row = get_conversation_context(conv_id)
        assert ctx_row is not None
        assert any("Replica count: 5" in f for f in ctx_row["structured_facts"])
        assert any("Replica count is 5, not 3" in f for f in ctx_row["structured_facts"])

        # Assemble context for follow-up question
        system_prompt, formatted_messages = context_service.assemble_context(
            conversation_id=conv_id,
            user_message="What is our current replica count?"
        )

        context_text = system_prompt + " " + " ".join([m["content"] for m in formatted_messages])
        assert "Replica count: 5" in context_text
        assert "Replica count is 5, not 3" in context_text

    finally:
        delete_conversation(conv_id)


def test_unrelated_older_content_not_polluting_context():
    """
    Verify that when the conversation moves on to a completely distinct subject,
    Layer D specific message retrieval does NOT pull in irrelevant historical facts.
    """
    conv = create_conversation("Switch Topic Test")
    conv_id = conv["id"]

    try:
        add_message(conv_id, "user", "My favorite car is a 1967 Shelby GT500 Fastback.")
        add_message(conv_id, "assistant", "A timeless classic muscle car, sir.")

        # 20 messages about baking bread
        for i in range(20):
            add_message(conv_id, "user", f"Baking step {i}: Sourdough fermentation status.")
            add_message(conv_id, "assistant", f"Fermentation step {i} is progressing well.")

        # Assemble context for a baking question
        system_prompt, formatted_messages = context_service.assemble_context(
            conversation_id=conv_id,
            user_message="What temperature should I set the oven to for baking sourdough?"
        )

        context_text = system_prompt + " " + " ".join([m["content"] for m in formatted_messages])
        # The car should not appear in Layer D retrieved messages since it's completely unrelated to sourdough baking
        assert "Shelby GT500" not in context_text

    finally:
        delete_conversation(conv_id)
