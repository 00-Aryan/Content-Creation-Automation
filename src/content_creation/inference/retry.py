"""Centralized retry infrastructure for the inference layer.

Provides retry policy configuration, error classification, delay calculation,
and retry metadata tracking. Designed as a foundation that providers can
adopt incrementally in future phases.
"""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 15.0
    backoff_factor: float = 2.0
    jitter: bool = False
    jitter_range: float = 0.5  # ±50% of calculated delay


@dataclass
class RetryAttempt:
    """Metadata for a single retry attempt."""

    attempt: int
    delay: float
    reason: str


@dataclass
class RetryState:
    """Tracks retry execution state across attempts."""

    policy: RetryPolicy
    attempts: list[RetryAttempt] = field(default_factory=list)

    @property
    def retries_used(self) -> int:
        return len(self.attempts)

    @property
    def should_retry(self) -> bool:
        return self.retries_used < self.policy.max_retries

    @property
    def total_delay(self) -> float:
        return sum(a.delay for a in self.attempts)


class RetryManager:
    """Centralized retry policy and delay calculation.

    Encapsulates retry classification, backoff timing, and logging
    so providers can delegate retry decisions without embedding policy.
    """

    def __init__(self, policy: Optional[RetryPolicy] = None):
        self._policy = policy or RetryPolicy()

    @property
    def policy(self) -> RetryPolicy:
        return self._policy

    def is_retryable(self, result: "InferenceResult") -> bool:
        """Classify whether a failed result warrants a retry.

        Relies exclusively on structured ProviderError metadata.
        Providers must normalize their exceptions into ProviderError
        so RetryManager remains provider-agnostic.
        """
        if result.provider_error is not None:
            return result.provider_error.retryable
        return False

    def calculate_delay(self, attempt: int) -> float:
        """Calculate backoff delay for a given attempt (0-indexed).

        Uses exponential backoff: base_delay * (backoff_factor ** attempt).
        Optionally applies jitter to spread retry storms.
        """
        delay = self._policy.base_delay * (self._policy.backoff_factor ** attempt)
        if self._policy.jitter:
            jitter_min = 1.0 - self._policy.jitter_range
            jitter_max = 1.0 + self._policy.jitter_range
            delay *= random.uniform(jitter_min, jitter_max)
        return round(delay, 2)

    def create_state(self) -> RetryState:
        """Create a fresh retry state for a new request."""
        return RetryState(policy=self._policy)

    def record_attempt(self, state: RetryState, attempt: int, reason: str) -> float:
        """Record a retry attempt and return the calculated delay.

        Args:
            state: Current retry state.
            attempt: Zero-indexed attempt number.
            reason: Human-readable reason for retry.

        Returns:
            Delay in seconds before next attempt.
        """
        delay = self.calculate_delay(attempt)
        state.attempts.append(RetryAttempt(attempt=attempt, delay=delay, reason=reason))
        self._log_retry(attempt, delay, reason)
        return delay

    def execute(self, fn: Callable[[], "InferenceResult"]) -> "InferenceResult":
        """Execute fn with retry logic controlled by this manager.

        Args:
            fn: Callable that performs a single inference attempt
                and returns an InferenceResult.

        Returns:
            InferenceResult from the successful attempt or final failure.
        """
        from content_creation.inference.providers.base import InferenceResult

        state = self.create_state()
        start = time.time()

        for attempt in range(self._policy.max_retries):
            result = fn()

            if result.success:
                result.retries = state.retries_used
                result.duration_seconds = round(time.time() - start, 2)
                return result

            # Use structured error metadata for retry decisions
            if not self.is_retryable(result):
                result.duration_seconds = round(time.time() - start, 2)
                return result

            # Still have retries left?
            if attempt < self._policy.max_retries - 1:
                reason = self._build_retry_reason(result)
                delay = self.record_attempt(state, attempt, reason)
                time.sleep(delay)

        # Exhausted retries
        duration = round(time.time() - start, 2)
        reason = self._build_retry_reason(result)
        return InferenceResult(
            text="",
            provider=result.provider,
            model=result.model,
            retries=state.retries_used,
            duration_seconds=duration,
            success=False,
            error=f"Max retries exhausted ({reason})",
            provider_error=result.provider_error,
        )

    def _build_retry_reason(self, result: "InferenceResult") -> str:
        """Build a human-readable retry reason from result metadata."""
        if result.provider_error is not None:
            pe = result.provider_error
            return f"category={pe.category.value} status={pe.status_code}"
        return f"error={result.error}"

    def _log_retry(self, attempt: int, delay: float, reason: str) -> None:
        """Emit structured retry log."""
        logger.warning(
            f"[retry] attempt={attempt + 1}/{self._policy.max_retries} "
            f"delay={delay}s reason={reason}"
        )
