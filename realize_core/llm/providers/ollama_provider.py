"""
Ollama LLM Provider: Stub for local/self-hosted LLM integration via Ollama.

To activate: install Ollama, pull a model, and set OLLAMA_HOST if not localhost.
No API key required — runs locally.
"""

import logging
import time

from realize_core.llm.base_provider import (
    BaseLLMProvider,
    Capability,
    LLMResponse,
    ModelInfo,
)

logger = logging.getLogger(__name__)

# Cached availability check (TTL-based to avoid blocking the event loop)
_availability_cache: bool | None = None
_availability_cache_time: float = 0.0
_AVAILABILITY_TTL = 60.0  # Cache for 60 seconds


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider (stub — ready for implementation)."""

    @property
    def name(self) -> str:
        return "ollama"

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                model_id="llama3.1:8b",
                display_name="Llama 3.1 8B (local)",
                tier=1,
                capabilities={Capability.TEXT, Capability.CODE},
                input_cost_per_m=0.0,
                output_cost_per_m=0.0,
                max_tokens=4096,
                context_window=128000,
            ),
            ModelInfo(
                model_id="deepseek-coder-v2:16b",
                display_name="DeepSeek Coder V2 (local)",
                tier=1,
                capabilities={Capability.TEXT, Capability.CODE},
                input_cost_per_m=0.0,
                output_cost_per_m=0.0,
                max_tokens=4096,
                context_window=128000,
            ),
        ]

    def is_available(self) -> bool:
        """Check if Ollama is running locally. Caches result for 60s to avoid blocking."""
        global _availability_cache, _availability_cache_time

        now = time.time()
        if _availability_cache is not None and (now - _availability_cache_time) < _AVAILABILITY_TTL:
            return _availability_cache

        try:
            import os

            import httpx

            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            resp = httpx.get(f"{host}/api/tags", timeout=2.0)
            _availability_cache = resp.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            _availability_cache = False

        _availability_cache_time = now
        return _availability_cache

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Text completion via Ollama API (stub)."""
        if not self.is_available():
            return LLMResponse(
                text="Ollama not running. Start Ollama and pull a model first.",
                model=model or "llama3.1:8b",
                provider=self.name,
                error="not_available",
            )

        # TODO: Implement when ready
        return LLMResponse(
            text="Ollama provider not yet implemented.",
            model=model or "llama3.1:8b",
            provider=self.name,
            error="not_implemented",
        )
