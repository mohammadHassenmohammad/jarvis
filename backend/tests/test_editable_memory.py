import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.database.db import (
    add_memory,
    get_memory,
    get_memories,
    update_memory,
    delete_memory,
    search_memories
)
from backend.app.tools.system_tools import (
    save_memory_tool,
    update_memory_tool,
    delete_memory_tool,
    search_memories_tool
)

client = TestClient(app)

def test_memory_crud_db():
    # 1. Add memory
    mem = add_memory("User prefers dark mode and concise answers", category="user_preference")
    assert mem["id"]
    mem_id = mem["id"]

    # 2. Get single memory
    fetched = get_memory(mem_id)
    assert fetched is not None
    assert fetched["content"] == "User prefers dark mode and concise answers"
    assert fetched["category"] == "user_preference"

    # 3. Update memory
    updated = update_memory(mem_id, "User prefers dark mode, high contrast, and brief answers", category="personal")
    assert updated is True

    fetched_after = get_memory(mem_id)
    assert fetched_after["content"] == "User prefers dark mode, high contrast, and brief answers"
    assert fetched_after["category"] == "personal"

    # 4. Search memories
    matches = search_memories(query="contrast")
    assert any(m["id"] == mem_id for m in matches)

    # 5. Delete memory
    deleted = delete_memory(mem_id)
    assert deleted is True
    assert get_memory(mem_id) is None

def test_memory_tools():
    # Save memory tool
    res_save = save_memory_tool(fact="User works on Python and React projects", category="work")
    assert res_save["success"] is True
    mem_id = res_save["memory_id"]

    # Search memory tool
    res_search = search_memories_tool(query="React")
    assert res_search["success"] is True
    assert any(m["id"] == mem_id for m in res_search["memories"])

    # Update memory tool
    res_update = update_memory_tool(memory_id=mem_id, content="User develops full-stack apps with Python, Vite, and React", category="work")
    assert res_update["success"] is True
    assert "full-stack apps" in res_update["content"]

    # Update non-existent memory
    res_update_invalid = update_memory_tool(memory_id="non-existent-id", content="Some text")
    assert res_update_invalid["success"] is False

    # Delete memory tool
    res_del = delete_memory_tool(memory_id=mem_id)
    assert res_del["success"] is True

    # Delete non-existent memory
    res_del_invalid = delete_memory_tool(memory_id="non-existent-id")
    assert res_del_invalid["success"] is False

def test_memory_api_endpoints():
    # POST /api/memories
    res_post = client.post("/api/memories", json={"content": "User drinks Earl Grey tea", "category": "user_preference"})
    assert res_post.status_code == 200
    mem_id = res_post.json()["memory"]["id"]

    # GET /api/memories/{id}
    res_get = client.get(f"/api/memories/{mem_id}")
    assert res_get.status_code == 200
    assert res_get.json()["memory"]["content"] == "User drinks Earl Grey tea"

    # GET /api/memories/search?q=Earl
    res_search = client.get("/api/memories/search?q=Earl")
    assert res_search.status_code == 200
    assert any(m["id"] == mem_id for m in res_search.json()["memories"])

    # PUT /api/memories/{id}
    res_put = client.put(f"/api/memories/{mem_id}", json={"content": "User drinks Earl Grey tea with lemon", "category": "personal"})
    assert res_put.status_code == 200
    assert res_put.json()["memory"]["content"] == "User drinks Earl Grey tea with lemon"
    assert res_put.json()["memory"]["category"] == "personal"

    # DELETE /api/memories/{id}
    res_del = client.delete(f"/api/memories/{mem_id}")
    assert res_del.status_code == 200

    # Verify 404 after deletion
    res_get_404 = client.get(f"/api/memories/{mem_id}")
    assert res_get_404.status_code == 404
