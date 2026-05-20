"""Gemini provider implementation."""

import logging
import time

from google import genai
from google.genai import errors

from content_creation.inference.providers.base import BaseProvider, InferenceResult

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Provider adapter for Google Gemini API."""

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
        """Call Gemini API with retry on 429 rate limits."""
        max_retries = 3
        base_delay = 15
        retries_used = 0
        start = time.time()

        for attempt in range(max_retries):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                )
                raw = response.text.strip().removeprefix("```json").removesuffix("```").strip()
                duration = time.time() - start
                return InferenceResult(
                    text=raw,
                    provider=self.provider_name,
                    model=self._model,
                    retries=retries_used,
                    duration_seconds=round(duration, 2),
                    success=True,
                )
            except errors.ClientError as e:
                if e.code == 429:
                    retries_used = attempt + 1
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Rate limited (429). Retrying in {delay}s "
                        f"(attempt {retries_used}/{max_retries})..."
                    )
                    time.sleep(delay)
                    continue
                duration = time.time() - start
                return InferenceResult(
                    text="",
                    provider=self.provider_name,
                    model=self._model,
                    retries=retries_used,
                    duration_seconds=round(duration, 2),
                    success=False,
                    error=str(e),
                )
            except Exception as e:
                duration = time.time() - start
                return InferenceResult(
                    text="",
                    provider=self.provider_name,
                    model=self._model,
                    retries=retries_used,
                    duration_seconds=round(duration, 2),
                    success=False,
                    error=str(e),
                )

        # Exhausted retries
        duration = time.time() - start
        return InferenceResult(
            text="",
            provider=self.provider_name,
            model=self._model,
            retries=retries_used,
            duration_seconds=round(duration, 2),
            success=False,
            error="Max retries exhausted (429 rate limiting)",
        )
