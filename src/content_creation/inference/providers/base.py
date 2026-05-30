"""Base provider abstraction for inference."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from content_creation.inference.models import ProviderError


@dataclass
class InferenceResult:
    """Result from a provider inference call."""

    text: str
    provider: str
    model: str
    retries: int
    duration_seconds: float
    success: bool
    error: Optional[str] = None
    provider_error: Optional[ProviderError] = None


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        ...

    @abstractmethod
    def generate(self, prompt: str) -> InferenceResult:
        """Generate a response from the provider.

        Args:
            prompt: The full prompt string to send.

        Returns:
            InferenceResult with the response text and metadata.
        """
        ...
