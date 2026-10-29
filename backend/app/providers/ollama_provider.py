import json
import httpx
from typing import AsyncGenerator, Any, Optional
from .base import BaseLLMProvider
from ..config import settings

class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    async def check_health(self) -> dict[str, Any]:
        """
        Check if Ollama is reachable and fetch available models.
        """
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    return {
                        "status": "connected",
                        "connected": True,
                        "url": self.base_url,
                        "models": models,
                        "message": f"Connected to Ollama. {len(models)} model(s) available."
                    }
                else:
                    return {
                        "status": "error",
                        "connected": False,
                        "url": self.base_url,
                        "models": [],
                        "message": f"Ollama returned HTTP status {res.status_code}"
                    }
        except httpx.ConnectError:
            return {
                "status": "disconnected",
                "connected": False,
                "url": self.base_url,
                "models": [],
                "message": (
                    "Cannot connect to Ollama at http://localhost:11434. "
                    "Please ensure the Ollama desktop app or service is running."
                )
            }
        except Exception as e:
            return {
                "status": "error",
                "connected": False,
                "url": self.base_url,
                "models": [],
                "message": f"Error contacting Ollama: {str(e)}"
            }

    async def list_models(self) -> list[str]:
        health = await self.check_health()
        return health.get("models", [])

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        model: str,
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.4,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream responses from Ollama /api/chat.
        """
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        # Performance tuned options
        options = {
            "temperature": temperature,
            "num_ctx": 2048,
            "num_predict": 512,  # Sufficient room for full response
            "top_k": 20,
            "top_p": 0.9,
        }

        # Ensure model resolution points to the single user-facing model: jarvis-latest-fast
        resolved_model = "jarvis-latest-fast" if ("jarvis" in model.lower() or model in ["qwen3:4b", "qwen2.5:1.5b", "default"] or not model) else model

        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": full_messages,
            "stream": True,
            "options": options,
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield {
                            "type": "error",
                            "data": f"Ollama API Error ({response.status_code}): {error_text.decode('utf-8', errors='ignore')}"
                        }
                        return

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        msg = chunk.get("message", {})
                        content = msg.get("content", "")
                        thinking = msg.get("thinking", "")
                        tool_calls = msg.get("tool_calls")
                        done = chunk.get("done", False)

                        if thinking:
                            yield {
                                "type": "thinking",
                                "data": thinking
                            }

                        if tool_calls:
                            yield {
                                "type": "tool_calls",
                                "data": tool_calls
                            }

                        if content:
                            yield {
                                "type": "content",
                                "data": content
                            }

                        if done:
                            yield {
                                "type": "done",
                                "data": {
                                    "total_duration": chunk.get("total_duration"),
                                    "eval_count": chunk.get("eval_count"),
                                }
                            }
                            return
        except httpx.ConnectError:
            yield {
                "type": "error",
                "data": (
                    "Cannot connect to Ollama at http://localhost:11434. "
                    "Make sure Ollama is launched and running on your Windows PC."
                )
            }
        except httpx.ReadTimeout:
            yield {
                "type": "error",
                "data": "Request timed out waiting for Ollama to generate a response."
            }
        except Exception as e:
            yield {
                "type": "error",
                "data": f"Unexpected error during Ollama stream: {str(e)}"
            }
