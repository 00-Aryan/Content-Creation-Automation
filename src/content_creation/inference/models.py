"""Structured error models for the inference layer."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ErrorCategory(Enum):
    """Provider-agnostic error classification."""

    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    INVALID_REQUEST = "invalid_request"
    SERVER_ERROR = "server_error"
    NETWORK = "network"
    UNKNOWN = "unknown"


@dataclass
class ProviderError:
    """Normalized provider error representation.

    Providers translate their specific exceptions into this structure
    so RetryManager can make decisions without provider-specific knowledge.
    """

    message: str
    retryable: bool
    status_code: Optional[int] = None
    category: ErrorCategory = ErrorCategory.UNKNOWN
    raw_error: Optional[str] = None
