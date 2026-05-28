"""Gemini provider implementation."""

import logging

from google import genai
from google.genai import errors

from content_creation.inference.models import ErrorCategory, ProviderError
from content_creation.inference.providers.base import BaseProvider, InferenceResult

logger = logging.getLogger(__name__)


def _classify_client_error(e: errors.ClientError) -> ProviderError:
    """Normalize a Gemini ClientError into a structured ProviderError."""
    code = getattr(e, "code", None)
    if code == 429:
        return ProviderError(
            message="Rate limited by Gemini API",
            retryable=True,
            status_code=429,
            category=ErrorCategory.RATE_LIMIT,
            raw_error=str(e),
        )
    if code in (401, 403):
        return ProviderError(
            message="Authentication/authorization failure",
            retryable=False,
            status_code=code,
            category=ErrorCategory.AUTH,
            raw_error=str(e),
        )
    if code == 400:
        return ProviderError(
            message="Invalid request",
            retryable=False,
            status_code=400,
            category=ErrorCategory.INVALID_REQUEST,
            raw_error=str(e),
        )
    if code and code >= 500:
        return ProviderError(
            message="Gemini server error",
            retryable=True,
            status_code=code,
            category=ErrorCategory.SERVER_ERROR,
            raw_error=str(e),
        )
    return ProviderError(
        message=str(e),
        retryable=False,
        status_code=code,
        category=ErrorCategory.UNKNOWN,
        raw_error=str(e),
    )


def _classify_generic_error(e: Exception) -> ProviderError:
    """Normalize an unexpected exception into a structured ProviderError."""
    return ProviderError(
        message=str(e),
        retryable=False,
        category=ErrorCategory.NETWORK if "connect" in str(e).lower() else ErrorCategory.UNKNOWN,
        raw_error=str(e),
    )


class GeminiProvider(BaseProvider):
    """Provider adapter for Google Gemini API (transport-only)."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str) -> InferenceResult:
        """Generate with retry — delegates to InferenceManager.

        Kept for backward compatibility. Direct callers should prefer
        using InferenceManager which owns retry orchestration.
        """
        return self.generate_once(prompt)

    def generate_once(self, prompt: str) -> InferenceResult:
        """Send a single request to Gemini. No retry logic."""
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
            )
            raw = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            return InferenceResult(
                text=raw,
                provider=self.provider_name,
                model=self._model,
                retries=0,
                duration_seconds=0.0,
                success=True,
            )
        except errors.ClientError as e:
            provider_error = _classify_client_error(e)
            return InferenceResult(
                text="",
                provider=self.provider_name,
                model=self._model,
                retries=0,
                duration_seconds=0.0,
                success=False,
                error=f"{e.code}: {e}",
                provider_error=provider_error,
            )
        except Exception as e:
            provider_error = _classify_generic_error(e)
            return InferenceResult(
                text="",
                provider=self.provider_name,
                model=self._model,
                retries=0,
                duration_seconds=0.0,
                success=False,
                error=str(e),
                provider_error=provider_error,
            )
