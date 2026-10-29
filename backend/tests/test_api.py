import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_root():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["system"] == "J.A.R.V.I.S."

def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_list_tools():
    res = client.get("/api/tools")
    assert res.status_code == 200
    data = res.json()
    assert "tools" in data
    assert "allowed_apps" in data

def test_settings_endpoints():
    res = client.get("/api/settings")
    assert res.status_code == 200
    assert "settings" in res.json()

    # Update setting
    put_res = client.put("/api/settings", json={"speech_rate": "1.2"})
    assert put_res.status_code == 200
    assert put_res.json()["settings"]["speech_rate"] == "1.2"

def test_conversations_flow():
    # 1. Create conversation
    res = client.post("/api/conversations", json={"title": "PyTest Session"})
    assert res.status_code == 200
    conv = res.json()["conversation"]
    cid = conv["id"]

    # 2. Get list
    list_res = client.get("/api/conversations")
    assert list_res.status_code == 200
    assert any(c["id"] == cid for c in list_res.json()["conversations"])

    # 3. Get single
    single_res = client.get(f"/api/conversations/{cid}")
    assert single_res.status_code == 200
    assert single_res.json()["conversation"]["id"] == cid

    # 4. Delete
    del_res = client.delete(f"/api/conversations/{cid}")
    assert del_res.status_code == 200
