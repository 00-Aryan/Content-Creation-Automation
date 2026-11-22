"""Tests for Gemini API authentication error classification and fail-fast circuit breaker."""

from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock, patch
import pytest
from google.genai import errors

from content_creation.application.brief_generation_service import BriefGenerationService
from content_creation.application.context import ApplicationContext
from content_creation.inference.models import ErrorCategory, ProviderError
from content_creation.inference.providers.gemini import (
    _classify_client_error,
    _classify_generic_error,
)
from content_creation.models.brief import Brief
from content_creation.models.topic import ScoredTopicItem, TopicStatus


def test_classify_client_error_api_key_invalid() -> None:
    """ERR-026: 400 error containing API_KEY_INVALID must classify as ErrorCategory.AUTH."""
    err = errors.ClientError(
        code=400,
        response_json={"error": {"message": "API_KEY_INVALID: API key not valid. Please pass a valid API key."}},
    )
    classified = _classify_client_error(err)
    assert classified.category == ErrorCategory.AUTH
    assert classified.status_code == 400
    assert classified.retryable is False
    assert "Invalid Gemini API key" in classified.message


def test_classify_client_error_other_400() -> None:
    """Standard 400 bad request remains ErrorCategory.INVALID_REQUEST."""
    err = errors.ClientError(
        code=400,
        response_json={"error": {"message": "INVALID_ARGUMENT: The parameter contents is malformed."}},
    )
    classified = _classify_client_error(err)
    assert classified.category == ErrorCategory.INVALID_REQUEST
    assert classified.status_code == 400
    assert classified.retryable is False


def test_classify_client_error_401_and_403() -> None:
    """Standard 401 and 403 classify as ErrorCategory.AUTH."""
    err_401 = errors.ClientError(code=401, response_json={"error": {"message": "Unauthorized"}})
    assert _classify_client_error(err_401).category == ErrorCategory.AUTH

    err_403 = errors.ClientError(code=403, response_json={"error": {"message": "Forbidden"}})
    assert _classify_client_error(err_403).category == ErrorCategory.AUTH


@pytest.mark.parametrize(
    "code,message,expected_category,expected_retryable",
    [
        (400, "API_KEY_INVALID: Invalid key provided", ErrorCategory.AUTH, False),
        (400, "Error: api_key_invalid detected in query", ErrorCategory.AUTH, False),
        (400, "API_KEY_INVALID_EXPIRED", ErrorCategory.AUTH, False),
        (400, "INVALID_ARGUMENT: Bad token contents", ErrorCategory.INVALID_REQUEST, False),
        (400, "FAILED_PRECONDITION: User region not supported", ErrorCategory.INVALID_REQUEST, False),
        (401, "UNAUTHENTICATED: Credentials rejected", ErrorCategory.AUTH, False),
        (403, "PERMISSION_DENIED: Quota tier insufficient", ErrorCategory.AUTH, False),
        (429, "RESOURCE_EXHAUSTED: Rate limit quota exceeded", ErrorCategory.RATE_LIMIT, True),
        (500, "INTERNAL: Internal server error", ErrorCategory.SERVER_ERROR, True),
        (503, "UNAVAILABLE: Backend service temporarily unavailable", ErrorCategory.SERVER_ERROR, True),
        (404, "NOT_FOUND: Model not found", ErrorCategory.UNKNOWN, False),
    ],
)
def test_classify_client_error_payload_variants(
    code: int,
    message: str,
    expected_category: ErrorCategory,
    expected_retryable: bool,
) -> None:
    """ERR-026 / RISK-001: Comprehensive BVA and classification across HTTP status codes and payloads."""
    err = errors.ClientError(code=code, response_json={"error": {"message": message}})
    classified = _classify_client_error(err)
    assert classified.category == expected_category
    assert classified.retryable is expected_retryable
    assert classified.status_code == code


def test_classify_generic_error_normalizes_exceptions() -> None:
    """ERR-026: Verify _classify_generic_error normalizes arbitrary exceptions to structured ProviderError."""
    # Exception containing 'connect' maps to ErrorCategory.NETWORK
    err_network = RuntimeError("Connection reset by peer during SSL handshake")
    classified_network = _classify_generic_error(err_network)
    assert classified_network.category == ErrorCategory.NETWORK
    assert classified_network.retryable is False
    assert classified_network.status_code is None
    assert "Connection reset" in classified_network.message

    # Other arbitrary exception maps to ErrorCategory.UNKNOWN
    err_unknown = ValueError("Unexpected malformed payload structure")
    classified_unknown = _classify_generic_error(err_unknown)
    assert classified_unknown.category == ErrorCategory.UNKNOWN
    assert classified_unknown.retryable is False
    assert classified_unknown.status_code is None
    assert "malformed payload" in classified_unknown.message


def test_brief_generation_aborts_immediately_on_auth_error(tmp_path: Path) -> None:
    """ERR-026 / REL-001: BriefGenerationService aborts batch loop immediately on non-retryable auth error."""
    ctx = ApplicationContext.create(tmp_path)
    for i in range(1, 4):
        item = ScoredTopicItem(
            id=f"topic-{i}",
            title=f"Paper Title {i}",
            url=f"https://arxiv.org/abs/240{i}.000",
            source="arxiv",
            published_at="2026-11-22T00:00:00Z",
            raw_text="A" * 200,
            status=TopicStatus.SCORED,
            priority_score=90.0 - i,
        )
        ctx.storage.save_scored(item)

    service = BriefGenerationService()
    call_count = 0

    def mock_generate_brief(item: ScoredTopicItem, prompt_registry: object, api_key: object) -> None:
        nonlocal call_count
        call_count += 1
        raise errors.ClientError(
            code=400,
            response_json={"error": {"message": "API_KEY_INVALID: API key not valid. Please pass a valid API key."}},
        )

    with patch(
        "content_creation.application.brief_generation_service.generate_brief",
        side_effect=mock_generate_brief,
    ):
        result = service.run(ctx, top_n=3, rate_limit_delay=0.0)

    # Must have failed fast on topic 1 and aborted before topics 2 and 3
    assert call_count == 1, f"Expected exactly 1 call before aborting, got {call_count}"
    assert result.generated_count == 0
    assert len(result.failures) == 1
    assert result.failures[0].topic_id == "topic-1"
    assert "API_KEY_INVALID" in result.failures[0].error


@pytest.mark.parametrize(
    "auth_exception_factory",
    [
        lambda: errors.ClientError(code=401, response_json={"error": {"message": "Unauthorized"}}),
        lambda: errors.ClientError(code=403, response_json={"error": {"message": "Forbidden"}}),
        lambda: ValueError("Google GenAI API key not found in environment"),
        lambda: RuntimeError("API_KEY_INVALID returned by inference manager"),
    ],
)
def test_brief_generation_circuit_breaker_auth_variants(
    tmp_path: Path,
    auth_exception_factory: Any,
) -> None:
    """ERR-026 / REL-001: BriefGenerationService aborts batch loop immediately on all auth exception variants."""
    ctx = ApplicationContext.create(tmp_path)
    for i in range(1, 5):
        item = ScoredTopicItem(
            id=f"topic-auth-var-{i}",
            title=f"Paper Title {i}",
            url=f"https://arxiv.org/abs/240{i}.000",
            source="arxiv",
            published_at="2026-11-22T00:00:00Z",
            raw_text="A" * 200,
            status=TopicStatus.SCORED,
            priority_score=90.0 - i,
        )
        ctx.storage.save_scored(item)

    service = BriefGenerationService()
    call_count = 0

    def mock_generate_brief(item: ScoredTopicItem, prompt_registry: object, api_key: object) -> None:
        nonlocal call_count
        call_count += 1
        raise auth_exception_factory()

    with patch(
        "content_creation.application.brief_generation_service.generate_brief",
        side_effect=mock_generate_brief,
    ):
        result = service.run(ctx, top_n=4, rate_limit_delay=0.0)

    # Circuit breaker must trip on item 1; items 2, 3, 4 must never be invoked
    assert call_count == 1
    assert result.generated_count == 0
    assert len(result.failures) == 1
    assert result.failures[0].topic_id == "topic-auth-var-1"


def test_brief_generation_auth_abort_zero_sleep_delay(tmp_path: Path) -> None:
    """ERR-026: When auth failure aborts the batch, rate-limit sleep delays must be completely bypassed."""
    ctx = ApplicationContext.create(tmp_path)
    for i in range(1, 4):
        item = ScoredTopicItem(
            id=f"topic-sleep-{i}",
            title=f"Paper Title {i}",
            url=f"https://arxiv.org/abs/240{i}.000",
            source="arxiv",
            published_at="2026-11-22T00:00:00Z",
            raw_text="A" * 200,
            status=TopicStatus.SCORED,
            priority_score=80.0,
        )
        ctx.storage.save_scored(item)

    service = BriefGenerationService()

    def mock_generate_brief(item: ScoredTopicItem, prompt_registry: object, api_key: object) -> None:
        raise errors.ClientError(code=401, response_json={"error": {"message": "Unauthorized"}})

    with patch(
        "content_creation.application.brief_generation_service.generate_brief",
        side_effect=mock_generate_brief,
    ), patch("time.sleep") as mock_sleep:
        result = service.run(ctx, top_n=3, rate_limit_delay=5.0)

    # time.sleep must NEVER be called because loop broke immediately
    assert mock_sleep.call_count == 0
    assert len(result.failures) == 1


def test_brief_generation_continues_on_transient_error(tmp_path: Path) -> None:
    """ERR-026: Verify BriefGenerationService continues across items when encountering transient/standard errors."""
    ctx = ApplicationContext.create(tmp_path)
    for i in range(1, 3):
        item = ScoredTopicItem(
            id=f"topic-transient-{i}",
            title=f"Paper Title {i}",
            url=f"https://arxiv.org/abs/240{i}.000",
            source="arxiv",
            published_at="2026-11-22T00:00:00Z",
            raw_text="A" * 200,
            status=TopicStatus.SCORED,
            priority_score=80.0,
        )
        ctx.storage.save_scored(item)

    service = BriefGenerationService()
    call_count = 0

    def mock_generate_brief(item: ScoredTopicItem, prompt_registry: object, api_key: object) -> None:
        nonlocal call_count
        call_count += 1
        raise ValueError(f"Temporary parsing glitch for {item.id}")

    with patch(
        "content_creation.application.brief_generation_service.generate_brief",
        side_effect=mock_generate_brief,
    ):
        result = service.run(ctx, top_n=2, rate_limit_delay=0.0)

    # Must process both items since this is not an auth circuit breaker condition
    assert call_count == 2
    assert len(result.failures) == 2


def test_brief_generation_topic_id_mismatch_records_failure_and_continues(tmp_path: Path) -> None:
    """Stage 3 Contract: Verify generated brief topic_id mismatch is recorded as failure and loop continues."""
    ctx = ApplicationContext.create(tmp_path)
    for i in range(1, 3):
        item = ScoredTopicItem(
            id=f"topic-mismatch-{i}",
            title=f"Paper Title {i}",
            url=f"https://arxiv.org/abs/240{i}.000",
            source="arxiv",
            published_at="2026-11-22T00:00:00Z",
            raw_text="A" * 200,
            status=TopicStatus.SCORED,
            priority_score=85.0,
        )
        ctx.storage.save_scored(item)

    service = BriefGenerationService()

    def mock_generate_brief(item: ScoredTopicItem, prompt_registry: object, api_key: object) -> Brief:
        return Brief(
            topic_id="completely-different-id",
            why_it_matters="Explanation",
            plain_english_summary=["Point 1", "Point 2", "Point 3"],
            student_takeaway="Takeaway",
            analogy="Analogy",
            limitation="Limitation",
            audience_fit="Audience",
            recommended_formats=["short_video"],
            source_url="https://example.com",
            generated_at="2026-11-22T00:00:00Z",
        )

    with patch(
        "content_creation.application.brief_generation_service.generate_brief",
        side_effect=mock_generate_brief,
    ):
        result = service.run(ctx, top_n=2, rate_limit_delay=0.0)

    # Both items had topic_id mismatch; both recorded as failures
    assert len(result.failures) == 2
    assert result.generated_count == 0
    assert "mismatch: expected topic-mismatch-1, got completely-different-id" in result.failures[0].error



def test_classify_client_error_api_key_invalid() -> None:
    """REL-001: 400 error containing API_KEY_INVALID must classify as ErrorCategory.AUTH."""
    err = errors.ClientError(
        code=400,
        response_json={"error": {"message": "API_KEY_INVALID: API key not valid. Please pass a valid API key."}},
    )
    classified = _classify_client_error(err)
    assert classified.category == ErrorCategory.AUTH
    assert classified.status_code == 400
    assert classified.retryable is False
    assert "Invalid Gemini API key" in classified.message


def test_classify_client_error_other_400() -> None:
    """Standard 400 bad request remains ErrorCategory.INVALID_REQUEST."""
    err = errors.ClientError(
        code=400,
        response_json={"error": {"message": "INVALID_ARGUMENT: The parameter contents is malformed."}},
    )
    classified = _classify_client_error(err)
    assert classified.category == ErrorCategory.INVALID_REQUEST
    assert classified.status_code == 400
    assert classified.retryable is False


def test_classify_client_error_401_and_403() -> None:
    """Standard 401 and 403 classify as ErrorCategory.AUTH."""
    err_401 = errors.ClientError(code=401, response_json={"error": {"message": "Unauthorized"}})
    assert _classify_client_error(err_401).category == ErrorCategory.AUTH

    err_403 = errors.ClientError(code=403, response_json={"error": {"message": "Forbidden"}})
    assert _classify_client_error(err_403).category == ErrorCategory.AUTH


def test_brief_generation_aborts_immediately_on_auth_error(tmp_path: Path) -> None:
    """REL-001: BriefGenerationService aborts batch loop immediately on non-retryable auth error."""
    # Setup test context with 3 scored topics
    ctx = ApplicationContext.create(tmp_path)
    scored_items = []
    for i in range(1, 4):
        item = ScoredTopicItem(
            id=f"topic-{i}",
            title=f"Paper Title {i}",
            url=f"https://arxiv.org/abs/240{i}.000",
            source="arxiv",
            published_at="2026-11-22T00:00:00Z",
            raw_text="A" * 200,
            status=TopicStatus.SCORED,
            priority_score=90.0 - i,
        )
        ctx.storage.save_scored(item)
        scored_items.append(item)

    service = BriefGenerationService()

    call_count = 0

    def mock_generate_brief(item: ScoredTopicItem, prompt_registry: object, api_key: object) -> None:
        nonlocal call_count
        call_count += 1
        raise errors.ClientError(
            code=400,
            response_json={"error": {"message": "API_KEY_INVALID: API key not valid. Please pass a valid API key."}},
        )

    with patch(
        "content_creation.application.brief_generation_service.generate_brief",
        side_effect=mock_generate_brief,
    ):
        result = service.run(ctx, top_n=3, rate_limit_delay=0.0)

    # Must have failed fast on topic 1 and aborted before topics 2 and 3
    assert call_count == 1, f"Expected exactly 1 call before aborting, got {call_count}"
    assert result.generated_count == 0
    assert len(result.failures) == 1
    assert result.failures[0].topic_id == "topic-1"
    assert "API_KEY_INVALID" in result.failures[0].error


def test_brief_generation_continues_on_transient_error(tmp_path: Path) -> None:
    """Verify BriefGenerationService continues across items when encountering transient/standard errors."""
    ctx = ApplicationContext.create(tmp_path)
    for i in range(1, 3):
        item = ScoredTopicItem(
            id=f"topic-transient-{i}",
            title=f"Paper Title {i}",
            url=f"https://arxiv.org/abs/240{i}.000",
            source="arxiv",
            published_at="2026-11-22T00:00:00Z",
            raw_text="A" * 200,
            status=TopicStatus.SCORED,
            priority_score=80.0,
        )
        ctx.storage.save_scored(item)

    service = BriefGenerationService()
    call_count = 0

    def mock_generate_brief(item: ScoredTopicItem, prompt_registry: object, api_key: object) -> None:
        nonlocal call_count
        call_count += 1
        raise ValueError(f"Temporary parsing glitch for {item.id}")

    with patch(
        "content_creation.application.brief_generation_service.generate_brief",
        side_effect=mock_generate_brief,
    ):
        result = service.run(ctx, top_n=2, rate_limit_delay=0.0)

    # Must process both items since this is not an auth circuit breaker condition
    assert call_count == 2
    assert len(result.failures) == 2

