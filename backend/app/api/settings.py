import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from ..database.db import get_all_settings, set_setting, get_setting
from ..providers.ollama_provider import OllamaProvider
from ..providers.gemini_provider import GeminiProvider
from ..tools.system_tools import get_system_status
from ..services.n8n_service import n8n_service
from ..config import settings

router = APIRouter(prefix="/api/settings", tags=["Settings"])
ollama = OllamaProvider()
gemini_provider = GeminiProvider()

MASKED_SECRET_PLACEHOLDER = "••••••••"

class UpdateSettingsRequest(BaseModel):
    model_config = {"extra": "allow"}
    model: Optional[str] = None
    provider: Optional[str] = None
    system_prompt: Optional[str] = None
    memory_enabled: Optional[str] = None
    voice_auto_speak: Optional[str] = None
    speech_rate: Optional[str] = None
    speech_pitch: Optional[str] = None
    voice_input_mode: Optional[str] = None
    wake_word_enabled: Optional[str] = None
    wake_word: Optional[str] = None
    preferred_voice: Optional[str] = None
    voice_language: Optional[str] = None
    vad_silence_timeout: Optional[str] = None
    voice_feedback: Optional[str] = None
    max_recording_duration: Optional[str] = None
    interrupt_on_wake: Optional[str] = None
    continuous_mode: Optional[str] = None
    whisper_backend_enabled: Optional[str] = None
    # n8n Webhook Settings
    n8n_enabled: Optional[str] = None
    n8n_webhook_url: Optional[str] = None
    n8n_auth_token: Optional[str] = None
    # Conversation Retrieval Settings
    retrieval_enabled: Optional[str] = None
    retrieval_limit: Optional[str] = None
    # Gemini Cloud Provider Settings
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None

class N8nTestRequest(BaseModel):
    webhook_url: Optional[str] = None
    auth_token: Optional[str] = None
    payload: Optional[dict[str, Any]] = None

def get_sanitized_settings() -> dict[str, str]:
    """Returns system settings with secrets masked to keep them out of frontend JavaScript."""
    all_s = get_all_settings()

    # Mask n8n auth token
    n8n_token = all_s.get("n8n_auth_token", "")
    if n8n_token and n8n_token.strip():
        all_s["n8n_has_token"] = "true"
        all_s["n8n_auth_token"] = MASKED_SECRET_PLACEHOLDER
    else:
        all_s["n8n_has_token"] = "false"
        all_s["n8n_auth_token"] = ""

    # Mask Gemini API key (reads from environment or DB)
    active_gemini_key = gemini_provider.api_key
    if active_gemini_key and active_gemini_key.strip():
        all_s["gemini_has_key"] = "true"
        all_s["gemini_api_key"] = MASKED_SECRET_PLACEHOLDER
    else:
        all_s["gemini_has_key"] = "false"
        all_s["gemini_api_key"] = ""

    # Ensure provider is explicitly set
    if "provider" not in all_s or not all_s["provider"]:
        all_s["provider"] = settings.DEFAULT_PROVIDER

    return all_s

@router.get("")
def read_settings():
    return {"settings": get_sanitized_settings()}

@router.put("")
def update_settings(req: UpdateSettingsRequest):
    req_dict = req.model_dump(exclude_unset=True)
    warning_message = None

    for k, v in req_dict.items():
        if v is None:
            continue

        str_v = str(v)

        # Protect masked secrets from overwriting stored credentials
        if k == "n8n_auth_token":
            if str_v == MASKED_SECRET_PLACEHOLDER or str_v.startswith("•••") or str_v.startswith("***"):
                continue
            if str_v.strip() in ("[CLEAR]", ""):
                set_setting(k, "")
            else:
                set_setting(k, str_v.strip())

        elif k == "gemini_api_key":
            if str_v == MASKED_SECRET_PLACEHOLDER or str_v.startswith("•••") or str_v.startswith("***"):
                continue
            if str_v.strip() in ("[CLEAR]", ""):
                set_setting(k, "")
            else:
                set_setting(k, str_v.strip())

        elif k == "provider":
            target_provider = str_v.strip().lower()
            if target_provider == "gemini":
                # Check if API key is present
                key_candidate = req_dict.get("gemini_api_key") or gemini_provider.api_key
                if not key_candidate or key_candidate in ("[CLEAR]", ""):
                    warning_message = (
                        "Switched to Google Gemini, but no GEMINI_API_KEY was found in environment or Settings. "
                        "Add an API key to enable responses."
                    )
            set_setting(k, target_provider)

        else:
            set_setting(k, str_v)

    response_data = {"settings": get_sanitized_settings(), "message": "Settings updated successfully"}
    if warning_message:
        response_data["warning"] = warning_message
    return response_data

@router.get("/providers")
async def get_providers():
    """Returns status and model lists for all supported providers."""
    active_p = get_setting("provider", settings.DEFAULT_PROVIDER)
    ollama_h = await ollama.check_health()
    gemini_h = await gemini_provider.check_health()

    return {
        "active_provider": active_p,
        "providers": {
            "ollama": {
                "name": "Ollama (Local GPU)",
                "type": "local",
                "free": True,
                "connected": ollama_h.get("connected", False),
                "status": ollama_h.get("status", "disconnected"),
                "models": ollama_h.get("models", []),
                "message": ollama_h.get("message", ""),
            },
            "gemini": {
                "name": "Google Gemini (Cloud AI)",
                "type": "cloud",
                "free": False,
                "connected": gemini_h.get("connected", False),
                "status": gemini_h.get("status", "unconfigured"),
                "has_key": bool(gemini_provider.api_key),
                "models": gemini_h.get("models", []),
                "message": gemini_h.get("message", ""),
            }
        }
    }

@router.post("/n8n/test")
def test_n8n_endpoint(req: N8nTestRequest):
    """
    Safely tests connectivity to the configured or provided n8n webhook.
    Validates URL, checks timeout, sends diagnostic ping, and returns status.
    """
    target_token = req.auth_token
    if not target_token or target_token.startswith("•••") or target_token.startswith("***"):
        target_token = get_setting("n8n_auth_token", "")

    result = n8n_service.trigger_webhook(
        workflow_name="jarvis_health_check",
        payload=req.payload or {"status": "ping", "system": "JARVIS"},
        webhook_url=req.webhook_url,
        auth_token=target_token,
        is_test=True
    )
    return result

@router.get("/system-status")
def system_health():
    return get_system_status()

@router.get("/ollama-status")
async def ollama_health():
    return await ollama.check_health()

@router.get("/ollama-models")
async def ollama_models():
    models = await ollama.list_models()
    return {"models": models}

@router.get("/gemini-status")
async def gemini_health():
    return await gemini_provider.check_health()

@router.get("/gemini-models")
async def gemini_models():
    models = await gemini_provider.list_models()
    return {"models": models}
