import os
import json
import logging
from typing import AsyncGenerator, Any, Optional
import httpx
from .base import BaseLLMProvider
from ..config import settings
from ..database.db import get_setting

logger = logging.getLogger("jarvis.gemini")

class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini Cloud Provider for JARVIS.
    
    Safety & Privacy Guarantees:
    - 100% Optional: Local Ollama / Qwen remains the default.
    - Cloud Cost Protection: Never dispatches requests without an explicit, valid API key.
    - Environment Variable Priority: Reads GEMINI_API_KEY from environment or .env.
    - Full Tool Calling: Translates allowlisted system tools into Gemini function declarations.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    DEFAULT_MODELS = [
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-2.5-flash"
    ]

    def __init__(self, api_key: Optional[str] = None):
        self._custom_key = api_key

    @property
    def api_key(self) -> str:
        """
        Resolves API key with priority:
        1. Explicit constructor argument
        2. Environment variable GEMINI_API_KEY
        3. Stored database setting
        """
        if self._custom_key and self._custom_key.strip():
            return self._custom_key.strip()
        env_key = os.getenv("GEMINI_API_KEY", "").strip()
        if env_key:
            return env_key
        db_key = get_setting("gemini_api_key", "").strip()
        if db_key and not db_key.startswith("•••") and not db_key.startswith("***"):
            return db_key
        return ""

    async def check_health(self) -> dict[str, Any]:
        """
        Verify Gemini API connectivity and API key validity.
        """
        key = self.api_key
        if not key:
            return {
                "status": "unconfigured",
                "connected": False,
                "models": self.DEFAULT_MODELS,
                "message": (
                    "Google Gemini is unconfigured. Set GEMINI_API_KEY in your environment (.env) "
                    "or Settings to activate cloud AI. Local Ollama remains active."
                )
            }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.BASE_URL}?key={key}")
                if res.status_code == 200:
                    data = res.json()
                    fetched = [
                        m.get("name", "").replace("models/", "")
                        for m in data.get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    gemini_models = [m for m in fetched if "gemini" in m]
                    models_list = gemini_models if gemini_models else self.DEFAULT_MODELS
                    return {
                        "status": "connected",
                        "connected": True,
                        "models": models_list,
                        "message": f"Connected to Google Gemini Cloud API ({len(models_list)} models available)."
                    }
                elif res.status_code in (400, 401, 403):
                    return {
                        "status": "error",
                        "connected": False,
                        "models": self.DEFAULT_MODELS,
                        "message": "Invalid Gemini API key or unauthorized access."
                    }
                else:
                    return {
                        "status": "error",
                        "connected": False,
                        "models": self.DEFAULT_MODELS,
                        "message": f"Gemini API returned HTTP status {res.status_code}"
                    }
        except httpx.ConnectError:
            return {
                "status": "disconnected",
                "connected": False,
                "models": self.DEFAULT_MODELS,
                "message": "Unable to connect to Google Gemini endpoint. Check internet connection."
            }
        except Exception as e:
            return {
                "status": "error",
                "connected": False,
                "models": self.DEFAULT_MODELS,
                "message": f"Gemini connection error: {str(e)}"
            }

    async def list_models(self) -> list[str]:
        health = await self.check_health()
        return health.get("models") or self.DEFAULT_MODELS

    def _convert_tools(self, tools: Optional[list[dict[str, Any]]]) -> Optional[list[dict[str, Any]]]:
        """Convert standard OpenAI-style tool declarations to Gemini functionDeclarations."""
        if not tools:
            return None

        declarations = []
        for t in tools:
            fn = t.get("function", {})
            name = fn.get("name")
            if not name:
                continue

            params = fn.get("parameters", {"type": "object", "properties": {}})
            # Sanitize parameters schema for Gemini
            cleaned_params = {
                "type": params.get("type", "object").upper() if isinstance(params.get("type"), str) else "OBJECT",
                "properties": params.get("properties", {}),
            }
            if params.get("required"):
                cleaned_params["required"] = params.get("required")

            declarations.append({
                "name": name,
                "description": fn.get("description", ""),
                "parameters": cleaned_params
            })

        return [{"functionDeclarations": declarations}] if declarations else None

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert standard conversation message history to Gemini contents format."""
        contents: list[dict[str, Any]] = []

        for m in messages:
            role = m.get("role")
            content = m.get("content", "")

            if role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": content or ""}]
                })

            elif role == "assistant":
                parts: list[dict[str, Any]] = []
                if content:
                    parts.append({"text": content})

                tool_calls = m.get("tool_calls")
                if tool_calls and isinstance(tool_calls, list):
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        fn_name = fn.get("name")
                        fn_args = fn.get("arguments", {})
                        if isinstance(fn_args, str):
                            try:
                                fn_args = json.loads(fn_args)
                            except Exception:
                                fn_args = {}
                        if fn_name:
                            parts.append({
                                "functionCall": {
                                    "name": fn_name,
                                    "args": fn_args if isinstance(fn_args, dict) else {}
                                }
                            })

                if not parts:
                    parts.append({"text": ""})

                contents.append({
                    "role": "model",
                    "parts": parts
                })

            elif role == "tool":
                # Send tool execution result to model as user functionResponse
                raw_res = content
                try:
                    res_dict = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
                except Exception:
                    res_dict = {"output": str(raw_res)}

                tool_name = m.get("tool") or m.get("name") or "system_tool"
                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": tool_name,
                            "response": res_dict if isinstance(res_dict, dict) else {"result": res_dict}
                        }
                    }]
                })

        return contents

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        model: str,
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.4,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream chat completions from Google Gemini v1beta API via Server-Sent Events.
        Never silently incurs charges: strictly verifies API key prior to request dispatch.
        """
        key = self.api_key
        if not key:
            yield {
                "type": "error",
                "data": (
                    "Google Gemini API key is missing. Set GEMINI_API_KEY in your environment or "
                    "Settings to activate cloud responses. Switch back to Ollama for 100% free local execution."
                )
            }
            return

        # Sanitize model name (fallback to fast flash model if local model name passed)
        clean_model = model.strip() if model else ""
        if not clean_model or "jarvis" in clean_model.lower() or "qwen" in clean_model.lower():
            clean_model = getattr(settings, "GEMINI_DEFAULT_MODEL", "gemini-1.5-flash")
        clean_model = clean_model.replace("models/", "")

        contents = self._convert_messages(messages)
        gemini_tools = self._convert_tools(tools)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024,
            }
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        if gemini_tools:
            payload["tools"] = gemini_tools

        url = f"{self.BASE_URL}/{clean_model}:streamGenerateContent?alt=sse&key={key}"

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status_code != 200:
                        err_bytes = await response.aread()
                        err_str = err_bytes.decode("utf-8", errors="ignore")
                        try:
                            err_json = json.loads(err_str)
                            msg = err_json.get("error", {}).get("message", err_str)
                        except Exception:
                            msg = err_str[:300]
                        yield {
                            "type": "error",
                            "data": f"Gemini Cloud Error ({response.status_code}): {msg}"
                        }
                        return

                    async for line in response.aiter_lines():
                        if not line.strip() or not line.startswith("data: "):
                            continue

                        raw_json = line[6:].strip()
                        if not raw_json:
                            continue

                        try:
                            chunk = json.loads(raw_json)
                        except json.JSONDecodeError:
                            continue

                        for candidate in chunk.get("candidates", []):
                            content_obj = candidate.get("content", {})
                            parts = content_obj.get("parts", [])

                            for part in parts:
                                # Handle text tokens
                                if "text" in part:
                                    yield {
                                        "type": "content",
                                        "data": part["text"]
                                    }

                                # Handle tool execution calls
                                if "functionCall" in part:
                                    fc = part["functionCall"]
                                    tool_call_obj = [{
                                        "id": f"call_{fc.get('name')}",
                                        "type": "function",
                                        "function": {
                                            "name": fc.get("name"),
                                            "arguments": fc.get("args", {})
                                        }
                                    }]
                                    yield {
                                        "type": "tool_calls",
                                        "data": tool_call_obj
                                    }

                    yield {
                        "type": "done",
                        "data": {"provider": "gemini", "model": clean_model}
                    }

        except httpx.ConnectError:
            yield {
                "type": "error",
                "data": "Could not connect to Google Gemini endpoint. Please check your internet connection."
            }
        except httpx.ReadTimeout:
            yield {
                "type": "error",
                "data": "Gemini API request timed out waiting for cloud stream response."
            }
        except Exception as e:
            yield {
                "type": "error",
                "data": f"Unexpected Gemini error: {str(e)}"
            }
