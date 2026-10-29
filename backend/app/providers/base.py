from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any, Optional

class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers (Ollama, Gemini, etc.).
    Allows modular swapping without touching UI, memory, or tools.
    """

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        model: str,
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream chat responses.
        Yields chunks: {"type": "content"|"tool_call"|"done"|"error", "data": ...}
        """
        pass

    @abstractmethod
    async def check_health(self) -> dict[str, Any]:
        """
        Check provider health, connectivity, and status.
        Returns: {"status": "ok"|"error", "message": "...", "models": [...]}
        """
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        """
        Return available model names.
        """
        pass
