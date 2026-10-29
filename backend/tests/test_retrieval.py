import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.database.db import (
    create_conversation,
    add_message,
    delete_conversation,
    search_relevant_conversations,
    set_setting
)
from backend.app.services.retrieval_service import retrieval_service
from backend.app.tools.system_tools import search_past_conversations_tool

client = TestClient(app)

def test_conversation_retrieval():
    # Setup test conversations
    conv1 = create_conversation(title="Quantum Propulsion Research")
    cid1 = conv1["id"]
    add_message(cid1, role="user", content="How do we stabilize the magnetic containment field for the arc reactor?")
    add_message(cid1, role="assistant", content="The magnetic coils must maintain a minimum harmonic resonance of 450 megaherz.")

    conv2 = create_conversation(title="Weekly Flight Diagnostics")
    cid2 = conv2["id"]
    add_message(cid2, role="user", content="Check thruster flight telemetry and rudder deflection angle.")
    add_message(cid2, role="assistant", content="All thrusters calibrated at 98.4% efficiency with nominal rudder control.")

    try:
        # 1. Direct search in DB
        matches = search_relevant_conversations(query="magnetic containment arc reactor", limit=3)
        assert len(matches) > 0
        assert any(m["conversation_id"] == cid1 for m in matches)
        assert "magnetic" in matches[0]["content"].lower() or "reactor" in matches[0]["content"].lower()

        # 2. Retrieval Service
        set_setting("retrieval_enabled", "true")
        snippets = retrieval_service.retrieve_context(query="What was the frequency for the magnetic containment field?")
        assert len(snippets) > 0
        assert any(s["conversation_id"] == cid1 for s in snippets)

        # 3. Formatted prompt context
        prompt_block = retrieval_service.format_context_for_prompt(snippets)
        assert "[Relevant Prior Conversation Context]:" in prompt_block
        assert "Quantum Propulsion Research" in prompt_block

        # 4. Search tool
        tool_res = search_past_conversations_tool(query="magnetic containment", limit=2)
        assert tool_res["success"] is True
        assert tool_res["count"] > 0
        assert any(r["conversation_id"] == cid1 for r in tool_res["results"])

        # 5. API endpoint GET /api/conversations/search
        api_res = client.get("/api/conversations/search?q=thruster+flight+telemetry")
        assert api_res.status_code == 200
        data = api_res.json()
        assert data["count"] > 0
        assert any(r["conversation_id"] == cid2 for r in data["results"])

        # 6. Test disabling retrieval
        set_setting("retrieval_enabled", "false")
        disabled_snippets = retrieval_service.retrieve_context(query="magnetic field")
        assert disabled_snippets == []

    finally:
        set_setting("retrieval_enabled", "true")
        delete_conversation(cid1)
        delete_conversation(cid2)
