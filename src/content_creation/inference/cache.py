"""Deterministic file-based inference cache."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from content_creation.inference.providers.base import InferenceResult

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path("data/cache/inference")


class InferenceCache:
    """File-based cache for successful inference results."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self._dir = cache_dir or _DEFAULT_CACHE_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _cache_key(prompt: str, provider: str, model: str) -> str:
        raw = f"{provider}:{model}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt: str, provider: str, model: str) -> Optional[InferenceResult]:
        key = self._cache_key(prompt, provider, model)
        path = self._dir / f"{key}.json"
        if not path.exists():
            logger.debug(f"[cache] miss key={key[:12]}")
            return None
        try:
            data = json.loads(path.read_text())
            logger.info(f"[cache] hit key={key[:12]} provider={provider} model={model}")
            return InferenceResult(
                text=data["text"],
                provider=data["provider"],
                model=data["model"],
                retries=0,
                duration_seconds=0.0,
                success=True,
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def put(self, prompt: str, result: InferenceResult) -> None:
        if not result.success:
            return
        key = self._cache_key(prompt, result.provider, result.model)
        path = self._dir / f"{key}.json"
        path.write_text(json.dumps({
            "text": result.text,
            "provider": result.provider,
            "model": result.model,
        }))
        logger.debug(f"[cache] write key={key[:12]} provider={result.provider}")
