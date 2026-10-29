import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.providers.gemini_provider import GeminiProvider
from backend.app.services.chat_service import chat_service
from backend.app.database.db import get_setting, set_setting

client = TestClient(app)

def test_gemini_api_key_resolution():
    # 1. Fallback when unconfigured
    provider_none = GeminiProvider(api_key=None)
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
        set_setting("gemini_api_key", "")
        assert provider_none.api_key == ""

    # 2. Environment variable priority
    with patch.dict(os.environ, {"GEMINI_API_KEY": "env-gemini-secret-12345"}):
        assert provider_none.api_key == "env-gemini-secret-12345"

    # 3. Explicit parameter takes top precedence
    provider_explicit = GeminiProvider(api_key="explicit-key-999")
    assert provider_explicit.api_key == "explicit-key-999"

@pytest.mark.asyncio
async def test_gemini_cost_protection_when_unconfigured():
    # Cloud cost protection: when no key is set, chat_stream must yield an error and NOT contact the cloud
    provider = GeminiProvider(api_key="")
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
        set_setting("gemini_api_key", "")
        chunks = []
        async for chunk in provider.chat_stream(
            messages=[{"role": "user", "content": "Hello"}],
            model="gemini-1.5-flash"
        ):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0]["type"] == "error"
        assert "Google Gemini API key is missing" in chunks[0]["data"]

@pytest.mark.asyncio
async def test_gemini_health_check_unconfigured_and_configured():
    provider = GeminiProvider(api_key="")
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
        set_setting("gemini_api_key", "")
        health = await provider.check_health()
        assert health["status"] == "unconfigured"
        assert health["connected"] is False

    # Configured mock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [
            {"name": "models/gemini-1.5-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-1.5-pro", "supportedGenerationMethods": ["generateContent"]},
        ]
    }

    provider_configured = GeminiProvider(api_key="test-api-key")
    with patch("httpx.AsyncClient.get", return_value=mock_response):
        h = await provider_configured.check_health()
        assert h["connected"] is True
        assert "gemini-1.5-flash" in h["models"]

@pytest.mark.asyncio
async def test_gemini_streaming_and_tool_call_parsing():
    provider = GeminiProvider(api_key="valid-test-key")

    # Mock SSE stream lines for text content and functionCall
    sse_lines = [
        'data: {"candidates": [{"content": {"parts": [{"text": "Analyzing request..."}]}}]}',
        'data: {"candidates": [{"content": {"parts": [{"functionCall": {"name": "get_system_time", "args": {}}}]}}]}',
    ]

    class MockAsyncStream:
        def __init__(self, status_code, lines):
            self.status_code = status_code
            self._lines = lines

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_lines(self):
            for line in self._lines:
                yield line

    mock_stream_ctx = MockAsyncStream(200, sse_lines)

    with patch("httpx.AsyncClient.stream", return_value=mock_stream_ctx):
        chunks = []
        async for c in provider.chat_stream(
            messages=[{"role": "user", "content": "What time is it?"}],
            model="gemini-1.5-flash",
            tools=[{"type": "function", "function": {"name": "get_system_time", "description": "Get current time"}}]
        ):
            chunks.append(c)

        # Verify text chunk and tool_calls chunk
        types = [c["type"] for c in chunks]
        assert "content" in types
        assert "tool_calls" in types
        assert "done" in types

        tool_chunk = next(c for c in chunks if c["type"] == "tool_calls")
        assert tool_chunk["data"][0]["function"]["name"] == "get_system_time"

def test_settings_api_gemini_privacy_and_providers():
    set_setting("gemini_api_key", "secret-key-12345")

    # 1. GET /api/settings MUST mask gemini_api_key as ••••••••
    res = client.get("/api/settings")
    assert res.status_code == 200
    settings = res.json()["settings"]
    assert settings["gemini_api_key"] == "••••••••"
    assert settings["gemini_has_key"] == "true"
    assert "secret-key-12345" not in str(res.json())

    # 2. PUT /api/settings with •••••••• preserves the secret
    put_res = client.put("/api/settings", json={"gemini_api_key": "••••••••", "provider": "gemini"})
    assert put_res.status_code == 200
    assert get_setting("gemini_api_key") == "secret-key-12345"

    # 3. GET /api/settings/providers returns both Ollama and Gemini
    prov_res = client.get("/api/settings/providers")
    assert prov_res.status_code == 200
    data = prov_res.json()
    assert "ollama" in data["providers"]
    assert "gemini" in data["providers"]
    assert data["providers"]["gemini"]["type"] == "cloud"
    assert data["providers"]["ollama"]["free"] is True

    # 4. Clean up: restore default provider to ollama
    client.put("/api/settings", json={"provider": "ollama"})
    assert get_setting("provider") == "ollama"

def test_chat_service_provider_selection():
    # Verify local Ollama is default
    set_setting("provider", "ollama")
    p1 = chat_service.get_provider()
    assert p1.__class__.__name__ == "OllamaProvider"

    # Switch to Gemini
    set_setting("provider", "gemini")
    p2 = chat_service.get_provider()
    assert p2.__class__.__name__ == "GeminiProvider"

    # Restore to default local Ollama
    set_setting("provider", "ollama")
    assert chat_service.get_provider().__class__.__name__ == "OllamaProvider"
