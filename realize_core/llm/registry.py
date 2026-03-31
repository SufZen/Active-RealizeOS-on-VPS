"""
Provider Registry: Central registry for LLM providers.

Maps model keys (e.g., "claude_sonnet") to provider instances.
Auto-discovers available providers at startup based on installed SDKs and API keys.
Includes per-model fallback chains (from provider_capabilities.yaml) and
a circuit breaker to temporarily disable failing providers.
"""

import logging
import time

from realize_core.llm.base_provider import BaseLLMProvider, Capability, ModelInfo

logger = logging.getLogger(__name__)

# Circuit breaker settings
_CB_FAILURE_THRESHOLD = 3  # Consecutive failures before opening circuit
_CB_RECOVERY_SECONDS = 60  # Seconds before trying a failed provider again


class ProviderRegistry:
    """Registry that maps model keys to LLM providers.

    Usage:
        registry = ProviderRegistry()
        registry.auto_register()  # Discovers available providers
        provider = registry.get_provider("claude_sonnet")
        response = await provider.complete(system_prompt, messages)
    """

    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}  # name → provider instance
        self._model_map: dict[str, str] = {}  # model_key → provider name
        self._fallback_chain: list[str] = []  # provider names in fallback order
        self._model_fallbacks: dict[str, list[str]] = {}  # model_key → [fallback model_keys]
        # Circuit breaker state
        self._failure_counts: dict[str, int] = {}  # provider_name → consecutive failures
        self._circuit_open_until: dict[str, float] = {}  # provider_name → timestamp

    def register(self, provider: BaseLLMProvider, model_keys: dict[str, str] | None = None):
        """Register a provider with optional model key mappings.

        Args:
            provider: The provider instance
            model_keys: Mapping of model_key → model_id
                         e.g., {"claude_sonnet": "claude-sonnet-4-6-20260217"}
        """
        self._providers[provider.name] = provider

        if model_keys:
            for key, model_id in model_keys.items():
                self._model_map[key] = provider.name

        logger.info(
            f"Registered provider: {provider.name} "
            f"(available={provider.is_available()}, models={len(provider.list_models())})"
        )

    def get_provider(self, model_key: str) -> BaseLLMProvider | None:
        """Get the provider for a given model key (e.g., 'claude_sonnet').

        Respects circuit breaker state — returns None if the provider's
        circuit is open (recently failed too many times).

        Args:
            model_key: The logical model key from config/router

        Returns:
            The provider instance, or None if not found or circuit is open.
        """
        provider_name = self._model_map.get(model_key)
        if not provider_name:
            return None

        # Check circuit breaker
        if self._is_circuit_open(provider_name):
            logger.debug(f"Circuit open for {provider_name}, skipping")
            return None

        return self._providers.get(provider_name)

    def get_provider_by_name(self, name: str) -> BaseLLMProvider | None:
        """Get a provider by its name (e.g., 'claude', 'gemini')."""
        return self._providers.get(name)

    def resolve_model_id(self, model_key: str) -> str | None:
        """Resolve a model key to its actual model ID string.

        Args:
            model_key: e.g., "claude_sonnet"

        Returns:
            The provider's model ID string (e.g., "claude-sonnet-4-6-20260217")
        """
        from realize_core.config import MODELS

        return MODELS.get(model_key)

    def get_fallback(self, model_key: str) -> BaseLLMProvider | None:
        """Get a fallback provider when the primary is unavailable.

        First tries per-model fallback chains (from YAML config), then
        walks the generic provider fallback chain. Skips providers with
        open circuits or that aren't available.
        """
        primary_name = self._model_map.get(model_key)

        # 1. Try per-model fallback chain (from provider_capabilities.yaml)
        model_chain = self._model_fallbacks.get(model_key, [])
        for fallback_key in model_chain:
            fb_provider_name = self._model_map.get(fallback_key)
            if fb_provider_name and fb_provider_name != primary_name:
                if self._is_circuit_open(fb_provider_name):
                    continue
                provider = self._providers.get(fb_provider_name)
                if provider and provider.is_available():
                    logger.info(f"Fallback: {model_key} → {fallback_key} (per-model chain)")
                    return provider

        # 2. Fall back to generic provider chain
        for provider_name in self._fallback_chain:
            if provider_name != primary_name:
                if self._is_circuit_open(provider_name):
                    continue
                provider = self._providers.get(provider_name)
                if provider and provider.is_available():
                    return provider

        return None

    def set_fallback_chain(self, chain: list[str]):
        """Set the provider fallback order.

        Args:
            chain: List of provider names in priority order
                   e.g., ["claude", "gemini", "openai", "ollama"]
        """
        self._fallback_chain = chain

    def set_model_fallbacks(self, fallbacks: dict[str, list[str]]):
        """Set per-model fallback chains (from provider_capabilities.yaml).

        Args:
            fallbacks: Mapping of model_key → list of fallback model_keys
                       e.g., {"claude_sonnet": ["gemini_pro", "gpt4o", "llama3"]}
        """
        self._model_fallbacks = fallbacks

    # -------------------------------------------------------------------
    # Circuit Breaker
    # -------------------------------------------------------------------

    def record_success(self, provider_name: str):
        """Record a successful call — resets the circuit breaker for this provider."""
        self._failure_counts[provider_name] = 0
        self._circuit_open_until.pop(provider_name, None)

    def record_failure(self, provider_name: str):
        """Record a failed call — may open the circuit breaker."""
        count = self._failure_counts.get(provider_name, 0) + 1
        self._failure_counts[provider_name] = count

        if count >= _CB_FAILURE_THRESHOLD:
            self._circuit_open_until[provider_name] = time.time() + _CB_RECOVERY_SECONDS
            logger.warning(
                f"Circuit breaker OPEN for {provider_name} "
                f"({count} consecutive failures, recovery in {_CB_RECOVERY_SECONDS}s)"
            )

    def _is_circuit_open(self, provider_name: str) -> bool:
        """Check if a provider's circuit breaker is currently open."""
        open_until = self._circuit_open_until.get(provider_name)
        if open_until is None:
            return False
        if time.time() >= open_until:
            # Recovery period elapsed — half-open: allow one try
            self._circuit_open_until.pop(provider_name, None)
            self._failure_counts[provider_name] = 0
            logger.info(f"Circuit breaker HALF-OPEN for {provider_name}, allowing retry")
            return False
        return True

    # -------------------------------------------------------------------
    # Query methods
    # -------------------------------------------------------------------

    def list_available(self) -> list[str]:
        """Return names of all currently available providers."""
        return [name for name, p in self._providers.items() if p.is_available()]

    def list_all(self) -> dict[str, bool]:
        """Return all registered providers with their availability status."""
        return {name: p.is_available() for name, p in self._providers.items()}

    def list_all_models(self) -> list[ModelInfo]:
        """Return all models across all available providers."""
        models = []
        for provider in self._providers.values():
            if provider.is_available():
                models.extend(provider.list_models())
        return models

    def providers_with_capability(self, capability: Capability) -> list[BaseLLMProvider]:
        """Find all available providers that support a specific capability."""
        return [p for p in self._providers.values() if p.is_available() and p.supports(capability)]

    def auto_register(self):
        """Auto-discover and register all known providers.

        Checks if each provider's SDK is installed and API key is configured.
        Only registers providers that pass is_available().
        Also loads per-model fallback chains from provider_capabilities.yaml.
        """
        from realize_core.config import MODELS

        # Claude
        try:
            from realize_core.llm.providers.claude_provider import ClaudeProvider

            claude = ClaudeProvider()
            self.register(
                claude,
                {
                    "claude_haiku": MODELS.get("claude_haiku", "claude-haiku-4-5-20251001"),
                    "claude_sonnet": MODELS.get("claude_sonnet", "claude-sonnet-4-6-20260217"),
                    "claude_opus": MODELS.get("claude_opus", "claude-opus-4-6-20260205"),
                },
            )
        except Exception as e:
            logger.debug(f"Claude provider not registered: {e}")

        # Gemini
        try:
            from realize_core.llm.providers.gemini_provider import GeminiProvider

            gemini = GeminiProvider()
            self.register(
                gemini,
                {
                    "gemini_flash": MODELS.get("gemini_flash", "gemini-2.5-flash"),
                    "gemini_pro": MODELS.get("gemini_pro", "gemini-3.1-pro-preview"),
                },
            )
        except Exception as e:
            logger.debug(f"Gemini provider not registered: {e}")

        # OpenAI (stub — registers but is_available will return False without SDK/key)
        try:
            from realize_core.llm.providers.openai_provider import OpenAIProvider

            openai_p = OpenAIProvider()
            self.register(
                openai_p,
                {
                    "gpt4o": "gpt-4o",
                    "gpt4o_mini": "gpt-4o-mini",
                },
            )
        except Exception as e:
            logger.debug(f"OpenAI provider not registered: {e}")

        # Ollama (stub — registers but is_available depends on local server)
        try:
            from realize_core.llm.providers.ollama_provider import OllamaProvider

            ollama = OllamaProvider()
            self.register(
                ollama,
                {
                    "llama3": "llama3.1:8b",
                    "deepseek_coder": "deepseek-coder-v2:16b",
                },
            )
        except Exception as e:
            logger.debug(f"Ollama provider not registered: {e}")

        # Default fallback chain: Claude → Gemini → OpenAI → Ollama
        self.set_fallback_chain(["claude", "gemini", "openai", "ollama"])

        # Load per-model fallback chains from provider_capabilities.yaml
        self._load_model_fallbacks()

        available = self.list_available()
        logger.info(
            f"Provider registry ready: {len(self._providers)} registered, "
            f"{len(available)} available ({', '.join(available) or 'none'})"
        )

    def _load_model_fallbacks(self):
        """Load per-model fallback chains from provider_capabilities.yaml."""
        try:
            from realize_core.llm.routing_engine import get_routing_engine

            engine = get_routing_engine()
            if engine.loaded:
                # The routing engine reads fallback chains from YAML
                for model_key in engine.models:
                    chain = engine.get_fallback_chain(model_key)
                    if chain:
                        self._model_fallbacks[model_key] = chain
                logger.info(f"Loaded {len(self._model_fallbacks)} per-model fallback chains")
        except Exception as e:
            logger.debug(f"Could not load per-model fallback chains: {e}")


# --- Module-level singleton ---

_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    """Get or create the global provider registry singleton."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
        _registry.auto_register()
    return _registry


def reset_registry():
    """Reset the registry (for testing)."""
    global _registry
    _registry = None
