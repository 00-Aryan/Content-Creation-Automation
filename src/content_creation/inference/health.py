"""Lightweight provider health tracking."""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_COOLDOWN_SECONDS = 60.0


@dataclass
class ProviderHealth:
    """Operational state for a single provider."""

    provider: str
    consecutive_failures: int = 0
    last_failure_at: Optional[float] = None
    last_success_at: Optional[float] = None
    cooldown_until: Optional[float] = None

    @property
    def in_cooldown(self) -> bool:
        if self.cooldown_until is None:
            return False
        return time.time() < self.cooldown_until


class HealthTracker:
    """Tracks operational health state for registered providers."""

    def __init__(self, cooldown_seconds: float = _DEFAULT_COOLDOWN_SECONDS):
        self._states: dict[str, ProviderHealth] = {}
        self._cooldown_seconds = cooldown_seconds

    def get(self, provider: str) -> ProviderHealth:
        if provider not in self._states:
            self._states[provider] = ProviderHealth(provider=provider)
        return self._states[provider]

    def record_success(self, provider: str) -> None:
        state = self.get(provider)
        state.consecutive_failures = 0
        state.last_success_at = time.time()
        state.cooldown_until = None
        logger.debug(f"[health] provider={provider} status=healthy")

    def record_failure(self, provider: str) -> None:
        state = self.get(provider)
        state.consecutive_failures += 1
        state.last_failure_at = time.time()
        if state.consecutive_failures >= 3:
            state.cooldown_until = time.time() + self._cooldown_seconds
            logger.warning(
                f"[health] provider={provider} status=cooldown "
                f"failures={state.consecutive_failures} "
                f"cooldown_seconds={self._cooldown_seconds}"
            )
        else:
            logger.debug(
                f"[health] provider={provider} status=degraded "
                f"failures={state.consecutive_failures}"
            )
