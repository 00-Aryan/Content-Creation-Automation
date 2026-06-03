"""Inference manager — lightweight routing to providers."""

import logging
from pathlib import Path
from typing import Optional

from content_creation.inference.cache import InferenceCache
from content_creation.inference.health import HealthTracker
from content_creation.inference.providers.base import BaseProvider, InferenceResult
from content_creation.inference.providers.gemini import GeminiProvider
from content_creation.inference.providers.openrouter import OpenRouterProvider
from content_creation.inference.retry import RetryManager

logger = logging.getLogger(__name__)

_PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
    "gemini": GeminiProvider,
    "openrouter": OpenRouterProvider,
}

_DEFAULT_PROVIDER = "gemini"


class InferenceManager:
    """Routes inference requests to the configured provider."""

    @staticmethod
    def is_available() -> bool:
        """Checks if the default generation service is available."""
        from content_creation.inference.credentials import resolve_credential
        return bool(resolve_credential("GEMINI_API_KEY"))

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = _DEFAULT_PROVIDER,
        model: Optional[str] = None,
        fallback: Optional[str] = None,
        fallback_api_key: Optional[str] = None,
        fallback_model: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        enable_cache: bool = True,
    ):
        from content_creation.inference.credentials import resolve_credential

        if not api_key:
            if provider == "gemini":
                api_key = resolve_credential("GEMINI_API_KEY")
            elif provider == "openrouter":
                api_key = resolve_credential("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError(f"API key not found for provider '{provider}'")

        if fallback is None:
            openrouter_key = resolve_credential("OPENROUTER_API_KEY")
            if openrouter_key:
                fallback = "openrouter"
                fallback_api_key = openrouter_key

        self._provider = self._build_provider(provider, api_key, model)
        self._fallback: Optional[BaseProvider] = None
        if fallback:
            self._fallback = self._build_provider(
                fallback, fallback_api_key or api_key, fallback_model
            )
        self._retry_manager = RetryManager()
        self._health = HealthTracker()
        self._cache = InferenceCache(cache_dir=cache_dir) if enable_cache else None

    @staticmethod
    def _build_provider(
        name: str, api_key: str, model: Optional[str]
    ) -> BaseProvider:
        provider_cls = _PROVIDER_REGISTRY.get(name)
        if provider_cls is None:
            raise ValueError(
                f"Unknown provider '{name}'. "
                f"Available: {list(_PROVIDER_REGISTRY.keys())}"
            )
        kwargs = {"api_key": api_key}
        if model is not None:
            kwargs["model"] = model
        return provider_cls(**kwargs)

    @property
    def health(self) -> HealthTracker:
        """Expose health tracker for external queries."""
        return self._health

    def generate(self, prompt: str, task_type: str = "general") -> InferenceResult:
        """Generate a response via the active provider, with optional failover.

        Args:
            prompt: Full prompt string.
            task_type: Label for logging (e.g. 'brief_generation').

        Returns:
            InferenceResult from the provider.
        """
        # Cache lookup
        if self._cache:
            cached = self._cache.get(
                prompt, self._provider.provider_name, self._provider.model_name
            )
            if cached is not None:
                return cached

        primary = self._provider
        primary_health = self._health.get(primary.provider_name)

        # If primary is in cooldown and fallback is available, skip to fallback
        if primary_health.in_cooldown and self._fallback:
            logger.warning(
                f"[failover] provider={primary.provider_name} reason=cooldown "
                f"fallback={self._fallback.provider_name}"
            )
            return self._execute_with(self._fallback, prompt, task_type)

        # Normal primary execution
        result = self._execute_with(primary, prompt, task_type)

        # If primary failed and fallback is configured, attempt single-step failover
        if not result.success and self._fallback:
            logger.warning(
                f"[failover] provider={primary.provider_name} reason=retry_exhausted "
                f"fallback={self._fallback.provider_name}"
            )
            return self._execute_with(self._fallback, prompt, task_type)

        return result

    def _execute_with(
        self, provider: BaseProvider, prompt: str, task_type: str
    ) -> InferenceResult:
        """Execute inference with a specific provider through retry infrastructure."""
        logger.info(
            f"[inference] task={task_type} provider={provider.provider_name} "
            f"model={provider.model_name}"
        )

        result = self._retry_manager.execute(
            lambda: provider.generate_once(prompt)
        )

        if result.success:
            self._health.record_success(result.provider)
            if self._cache:
                self._cache.put(prompt, result)
        else:
            self._health.record_failure(result.provider)

        logger.info(
            f"[inference] task={task_type} success={result.success} "
            f"retries={result.retries} duration={result.duration_seconds}s"
        )
        if not result.success:
            logger.warning(f"[inference] task={task_type} error={result.error}")

        return result
