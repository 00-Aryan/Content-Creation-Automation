"""Tests for Gemini API authentication error classification and fail-fast circuit breaker."""

from pathlib import Path
from unittest.mock import patch
import pytest
from google.genai import errors

from content_creation.application.brief_generation_service import BriefGenerationService
from content_creation.application.context import ApplicationContext
from content_creation.inference.models import ErrorCategory, ProviderError
from content_creation.inference.providers.gemini import _classify_client_error
from content_creation.models.topic import ScoredTopicItem, TopicStatus


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

