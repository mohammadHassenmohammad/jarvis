import pytest
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_transcribe_empty():
    response = client.post("/api/voice/transcribe", files={"file": ("test.wav", b"", "audio/wav")})
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == ""

def test_voice_endpoint_registered():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"
