import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.database.db import get_setting, set_setting
from backend.app.services.n8n_service import n8n_service
from backend.app.tools.system_tools import trigger_n8n_webhook

client = TestClient(app)

def test_n8n_url_validation():
    # Valid URLs
    valid, err = n8n_service.validate_webhook_url("http://localhost:5678/webhook/test")
    assert valid is True
    assert err == ""

    valid, err = n8n_service.validate_webhook_url("https://automation.myhome.net/webhook/jarvis")
    assert valid is True

    valid, err = n8n_service.validate_webhook_url("http://192.168.1.100:5678/webhook/deploy")
    assert valid is True

    # Invalid Schemes
    valid, err = n8n_service.validate_webhook_url("ftp://localhost:5678/webhook")
    assert valid is False
    assert "protocol scheme" in err

    valid, err = n8n_service.validate_webhook_url("file:///etc/passwd")
    assert valid is False

    # Blocked SSRF Metadata Targets
    valid, err = n8n_service.validate_webhook_url("http://169.254.169.254/latest/meta-data")
    assert valid is False
    assert "blocked for security" in err

    valid, err = n8n_service.validate_webhook_url("http://metadata.google.internal/computeMetadata/v1/")
    assert valid is False
    assert "blocked for security" in err

    # Empty / malformed
    valid, err = n8n_service.validate_webhook_url("")
    assert valid is False

    valid, err = n8n_service.validate_webhook_url("not-a-url")
    assert valid is False

def test_n8n_disabled_by_default():
    set_setting("n8n_enabled", "false")
    set_setting("n8n_webhook_url", "http://localhost:5678/webhook/test")

    # When disabled, trigger_webhook must return disabled status immediately without network calls
    res = n8n_service.trigger_webhook("deploy_protocol")
    assert res["success"] is False
    assert res.get("disabled") is True
    assert "currently disabled in Settings" in res["error"]

    # Tool invocation also safely respects disabled state
    tool_res = trigger_n8n_webhook("deploy_protocol")
    assert tool_res["success"] is False
    assert tool_res.get("disabled") is True

def test_n8n_mock_dispatch():
    set_setting("n8n_enabled", "true")
    set_setting("n8n_webhook_url", "http://localhost:5678/webhook/test")
    set_setting("n8n_auth_token", "super-secret-n8n-token-12345")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "workflowId": "42"}

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        res = n8n_service.trigger_webhook("lights_on", payload={"room": "lab", "brightness": 100})
        assert res["success"] is True
        assert res["status_code"] == 200

        # Verify headers included auth token and content type
        called_args, called_kwargs = mock_post.call_args
        headers = called_kwargs["headers"]
        assert headers["Authorization"] == "Bearer super-secret-n8n-token-12345"
        assert headers["X-N8N-API-KEY"] == "super-secret-n8n-token-12345"

        # Verify payload structure preserves privacy (no conversational leak)
        body = called_kwargs["json"]
        assert body["source"] == "JARVIS"
        assert body["action"] == "lights_on"
        assert body["payload"] == {"room": "lab", "brightness": 100}

def test_n8n_secret_privacy_in_settings_api():
    set_setting("n8n_enabled", "true")
    set_setting("n8n_webhook_url", "http://localhost:5678/webhook/test")
    set_setting("n8n_auth_token", "top-secret-token-xyz")

    # 1. GET /api/settings MUST NOT return top-secret-token-xyz
    res = client.get("/api/settings")
    assert res.status_code == 200
    settings = res.json()["settings"]
    assert settings["n8n_auth_token"] == "••••••••"
    assert settings["n8n_has_token"] == "true"
    assert "top-secret-token-xyz" not in str(res.json())

    # 2. PUT /api/settings with masked placeholder MUST NOT overwrite stored secret
    put_res = client.put("/api/settings", json={"n8n_auth_token": "••••••••", "n8n_enabled": "true"})
    assert put_res.status_code == 200
    # Direct DB verification
    assert get_setting("n8n_auth_token") == "top-secret-token-xyz"

    # 3. PUT /api/settings with new token updates stored secret
    put_new = client.put("/api/settings", json={"n8n_auth_token": "new-rotated-token-999"})
    assert put_new.status_code == 200
    assert get_setting("n8n_auth_token") == "new-rotated-token-999"

    # 4. PUT /api/settings with "" or "[CLEAR]" clears token
    put_clear = client.put("/api/settings", json={"n8n_auth_token": ""})
    assert put_clear.status_code == 200
    assert get_setting("n8n_auth_token") == ""

    # Clean up
    set_setting("n8n_enabled", "false")
    set_setting("n8n_webhook_url", "")
    set_setting("n8n_auth_token", "")

def test_n8n_test_endpoint():
    with patch.object(
        n8n_service,
        "trigger_webhook",
        return_value={"success": True, "status_code": 200, "message": "Pong"}
    ) as mock_trig:
        res = client.post("/api/settings/n8n/test", json={
            "webhook_url": "http://localhost:5678/webhook/test",
            "auth_token": "test-token"
        })
        assert res.status_code == 200
        assert res.json()["success"] is True
        mock_trig.assert_called_once()
