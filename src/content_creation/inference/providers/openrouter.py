"""OpenRouter provider implementation."""

import logging

import requests

from content_creation.inference.models import ErrorCategory, ProviderError
from content_creation.inference.providers.base import BaseProvider, InferenceResult

logger = logging.getLogger(__name__)

_API_URL = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"


def _classify_http_error(status_code: int, body: str) -> ProviderError:
    """Normalize an HTTP error response into a structured ProviderError."""
    if status_code == 429:
        return ProviderError(
            message="Rate limited by OpenRouter API",
            retryable=True,
            status_code=429,
            category=ErrorCategory.RATE_LIMIT,
            raw_error=body,
        )
    if status_code in (401, 403):
        return ProviderError(
            message="Authentication/authorization failure",
            retryable=False,
            status_code=status_code,
            category=ErrorCategory.AUTH,
            raw_error=body,
        )
    if status_code == 400:
        return ProviderError(
            message="Invalid request",
            retryable=False,
            status_code=400,
            category=ErrorCategory.INVALID_REQUEST,
            raw_error=body,
        )
    if status_code >= 500:
        return ProviderError(
            message="OpenRouter server error",
            retryable=True,
            status_code=status_code,
            category=ErrorCategory.SERVER_ERROR,
            raw_error=body,
        )
    return ProviderError(
        message=f"HTTP {status_code}",
        retryable=False,
        status_code=status_code,
        category=ErrorCategory.UNKNOWN,
        raw_error=body,
    )


def _classify_generic_error(e: Exception) -> ProviderError:
    """Normalize a network/unexpected exception into a structured ProviderError."""
    return ProviderError(
        message=str(e),
        retryable=False,
        category=ErrorCategory.NETWORK if "connect" in str(e).lower() else ErrorCategory.UNKNOWN,
        raw_error=str(e),
    )


class OpenRouterProvider(BaseProvider):
    """Provider adapter for OpenRouter API (OpenAI-compatible)."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL):
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str) -> InferenceResult:
        """Generate — delegates to generate_once (retry owned by InferenceManager)."""
        return self.generate_once(prompt)

    def generate_once(self, prompt: str) -> InferenceResult:
        """Send a single request to OpenRouter. No retry logic."""
        try:
            resp = requests.post(
                _API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60,
            )

            if resp.status_code != 200:
                provider_error = _classify_http_error(resp.status_code, resp.text)
                return InferenceResult(
                    text="",
                    provider=self.provider_name,
                    model=self._model,
                    retries=0,
                    duration_seconds=0.0,
                    success=False,
                    error=f"{resp.status_code}: {resp.text[:200]}",
                    provider_error=provider_error,
                )

            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            text = text.removeprefix("```json").removesuffix("```").strip()
            return InferenceResult(
                text=text,
                provider=self.provider_name,
                model=self._model,
                retries=0,
                duration_seconds=0.0,
                success=True,
            )

        except (requests.RequestException, KeyError, IndexError) as e:
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
