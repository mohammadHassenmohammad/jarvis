import json
import logging
from typing import Any, Optional
from urllib.parse import urlparse
import httpx
from datetime import datetime
from ..database.db import get_setting
from ..config import settings

logger = logging.getLogger("jarvis.n8n")

class N8nService:
    """
    Self-hosted n8n Webhook Integration Service.
    
    Privacy & Security Guarantees:
    - 100% Optional: Disabled by default. Will not dispatch requests if disabled.
    - Strict Request Validation: Validates URL scheme (http/https), blocks cloud metadata SSRF.
    - Data Privacy: Dispatches only user-specified action payloads; never exports conversations or keys.
    - Secret Protection: Auth tokens and headers are never logged or returned to client interfaces.
    """

    FORBIDDEN_HOSTS = {
        "169.254.169.254",         # AWS/GCP/Azure link-local metadata
        "metadata.google.internal", # GCP internal metadata
        "instance-data",            # AWS legacy metadata
    }

    @classmethod
    def validate_webhook_url(cls, url: Optional[str]) -> tuple[bool, str]:
        if not url or not url.strip():
            return False, "Webhook URL cannot be empty."

        clean_url = url.strip()
        try:
            parsed = urlparse(clean_url)
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"

        if parsed.scheme.lower() not in ("http", "https"):
            return False, f"Invalid protocol scheme '{parsed.scheme}'. Only http:// and https:// are permitted."

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False, "Webhook URL must contain a valid hostname or IP address."

        if hostname in cls.FORBIDDEN_HOSTS:
            return False, f"Host '{hostname}' is blocked for security reasons."

        return True, ""

    @classmethod
    def is_enabled(cls) -> bool:
        return get_setting("n8n_enabled", "false").lower() == "true"

    @classmethod
    def trigger_webhook(
        cls,
        workflow_name: str = "default",
        payload: Optional[dict[str, Any]] = None,
        webhook_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        is_test: bool = False
    ) -> dict[str, Any]:
        """
        Safely trigger an n8n webhook endpoint with payload and optional secret authentication.
        """
        # Enforce opt-in setting unless this is an explicit connection test
        if not is_test and not cls.is_enabled():
            return {
                "success": False,
                "disabled": True,
                "error": "n8n integration is currently disabled in Settings. Enable it to trigger automated workflows."
            }

        target_url = (webhook_url or get_setting("n8n_webhook_url", "")).strip()
        is_valid, err_msg = cls.validate_webhook_url(target_url)
        if not is_valid:
            return {
                "success": False,
                "error": err_msg
            }

        # Resolve auth token (masked values '••••••••' or None fallback to database setting)
        token = auth_token
        if not token or token.startswith("•••") or token.startswith("***"):
            token = get_setting("n8n_auth_token", "")
        token = (token or "").strip()

        # Build headers
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "JARVIS-AI-Assistant/1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}" if not token.lower().startswith("bearer ") else token
            headers["X-N8N-API-KEY"] = token

        # Build clean, privacy-preserving payload
        body_data: dict[str, Any] = {
            "source": "JARVIS",
            "action": workflow_name or "default",
            "timestamp": datetime.now().isoformat(),
            "payload": payload if isinstance(payload, dict) else {"message": str(payload or "")}
        }

        timeout_sec = getattr(settings, "N8N_REQUEST_TIMEOUT_SEC", 8.0)

        try:
            with httpx.Client(timeout=timeout_sec, follow_redirects=True) as client:
                res = client.post(target_url, json=body_data, headers=headers)

                res_data = None
                try:
                    res_data = res.json()
                except Exception:
                    res_data = res.text[:500] if res.text else None

                if 200 <= res.status_code < 300:
                    return {
                        "success": True,
                        "status_code": res.status_code,
                        "workflow": workflow_name,
                        "response": res_data,
                        "message": f"Successfully triggered n8n workflow '{workflow_name}' (Status {res.status_code})."
                    }
                else:
                    return {
                        "success": False,
                        "status_code": res.status_code,
                        "response": res_data,
                        "error": f"n8n webhook responded with status {res.status_code}."
                    }

        except httpx.ConnectError:
            return {
                "success": False,
                "error": f"Failed to connect to n8n at '{target_url}'. Ensure your self-hosted n8n instance is running and reachable."
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": f"Connection to n8n webhook at '{target_url}' timed out after {timeout_sec}s."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"n8n webhook execution failed: {str(e)}"
            }

    @classmethod
    def test_connection(
        cls,
        webhook_url: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Verify connectivity to an n8n webhook without modifying system state.
        """
        test_payload = {
            "test": True,
            "message": "JARVIS diagnostic ping",
            "status": "ping"
        }
        return cls.trigger_webhook(
            workflow_name="diagnostic_ping",
            payload=test_payload,
            webhook_url=webhook_url,
            auth_token=auth_token,
            is_test=True
        )

n8n_service = N8nService()
