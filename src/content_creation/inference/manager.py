"""Inference manager — lightweight routing to providers."""

import logging

from content_creation.inference.providers.base import InferenceResult
from content_creation.inference.providers.gemini import GeminiProvider

logger = logging.getLogger(__name__)


class InferenceManager:
    """Routes inference requests to the configured provider."""

    def __init__(self, api_key: str):
        self._provider = GeminiProvider(api_key=api_key)

    def generate(self, prompt: str, task_type: str = "general") -> InferenceResult:
        """Generate a response via the active provider.

        Args:
            prompt: Full prompt string.
            task_type: Label for logging (e.g. 'brief_generation').

        Returns:
            InferenceResult from the provider.
        """
        logger.info(
            f"[inference] task={task_type} provider={self._provider.provider_name} "
            f"model={self._provider.model_name}"
        )

        result = self._provider.generate(prompt)

        logger.info(
            f"[inference] task={task_type} success={result.success} "
            f"retries={result.retries} duration={result.duration_seconds}s"
        )
        if not result.success:
            logger.warning(f"[inference] task={task_type} error={result.error}")

        return result
