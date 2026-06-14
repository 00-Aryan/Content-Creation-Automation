import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from content_creation.generation.linkedin import LinkedInPostGenerator
from content_creation.models.brief import Brief
from content_creation.models.linkedin import LinkedInPost
from content_creation.shared.enums import ReviewStatus


@pytest.fixture
def sample_brief():
    """Create a sample Brief for testing."""
    return Brief(
        topic_id="test_topic_123",
        why_it_matters="Transformers revolutionized NLP",
        plain_english_summary=[
            "Transformers use attention to process text",
            "They can handle long-range dependencies",
            "Pre-training + fine-tuning is the key paradigm",
        ],
        student_takeaway="Learn Transformers fundamentals before advanced topics",
        analogy="Think of attention as a smart spotlight that highlights relevant words",
        limitation="Requires lots of compute and data",
        audience_fit="Intermediate ML students with Python experience",
        recommended_formats=["short_video", "carousel"],
        source_url="https://arxiv.org/abs/1706.03762",
        review_status=ReviewStatus.DRAFT,
        generated_at="2026-05-14T10:00:00Z",
    )


@pytest.fixture
def prompt_dir(tmp_path):
    """Prompt file required by LinkedInPostGenerator."""
    (tmp_path / "linkedin_post.md").write_text("Test prompt")
    return tmp_path


@pytest.fixture
def valid_linkedin_response():
    """Valid JSON response from Gemini for a LinkedIn post."""
    return json.dumps(
        {
            "hook": "What if machines could read entire documents instantly?",
            "post_body": "LinkedIn ready post body goes here.",
            "takeaway": "Actionable takeaway.",
            "cta": "What do you think about this?",
            "hashtags": ["#AI", "#MachineLearning", "#Transformers"],
            "source_reference": "Paper: Attention Is All You Need",
            "claims_used": [
                "Transformers use attention to process text",
                "They can handle long-range dependencies",
            ],
            "review_status": "draft",
        }
    )


def _make_inference_result(text, success=True):
    """Helper to create a mock InferenceResult."""
    from content_creation.inference.providers.base import InferenceResult

    return InferenceResult(
        text=text,
        provider="gemini",
        model="gemini-2.5-flash",
        retries=0,
        duration_seconds=1.0,
        success=success,
        error=None if success else "error",
    )


def test_generate_linkedin_success(sample_brief, valid_linkedin_response, prompt_dir):
    """1. Test successful LinkedIn post generation from valid JSON."""
    with patch(
        "content_creation.generation.linkedin.InferenceManager"
    ) as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_linkedin_response)

        generator = LinkedInPostGenerator(api_key="test_api_key", prompt_dir=prompt_dir)
        post = generator.generate(None, sample_brief)

    assert isinstance(post, LinkedInPost)
    assert post.topic_id == sample_brief.topic_id
    assert post.hook == "What if machines could read entire documents instantly?"
    assert post.post_body == "LinkedIn ready post body goes here."
    assert post.takeaway == "Actionable takeaway."
    assert post.cta == "What do you think about this?"
    assert post.hashtags == ["#AI", "#MachineLearning", "#Transformers"]
    assert post.source_reference == "Paper: Attention Is All You Need"
    assert post.source_links == ["https://arxiv.org/abs/1706.03762"]
    assert post.review_status == ReviewStatus.DRAFT


def test_generate_linkedin_malformed_json_fallback(sample_brief, prompt_dir):
    """2. Test fallback behavior when inference returns malformed JSON."""
    with patch(
        "content_creation.generation.linkedin.InferenceManager"
    ) as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result("invalid json")

        generator = LinkedInPostGenerator(api_key="test_api_key", prompt_dir=prompt_dir)
        post = generator.generate(None, sample_brief)

    assert isinstance(post, LinkedInPost)
    assert post.topic_id == sample_brief.topic_id
    assert post.hook == "needs_review"
    assert post.post_body == "needs_review"
    assert post.review_status == ReviewStatus.NEEDS_REVIEW


def test_generate_linkedin_missing_fields_fallback(sample_brief, prompt_dir):
    """3. Test missing optional/generated fields are handled safely."""
    # JSON missing hook and cta
    partial_response = json.dumps(
        {
            "post_body": "Partial body",
            "takeaway": "Partial takeaway",
            "hashtags": ["#AI", "#ML", "#DeepLearning"],
            "source_reference": "Reference",
            "claims_used": ["claim"],
            "review_status": "draft",
        }
    )
    with patch(
        "content_creation.generation.linkedin.InferenceManager"
    ) as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(partial_response)

        generator = LinkedInPostGenerator(api_key="test_api_key", prompt_dir=prompt_dir)
        post = generator.generate(None, sample_brief)

    assert isinstance(post, LinkedInPost)
    assert post.topic_id == sample_brief.topic_id
    assert post.hook == "needs_review"
    assert post.cta == "needs_review"
    assert post.post_body == "Partial body"
    assert post.review_status == ReviewStatus.DRAFT


def test_generate_linkedin_source_url_preserved(
    sample_brief, valid_linkedin_response, prompt_dir
):
    """4. Test that source URL from the brief is preserved in source_links."""
    with patch(
        "content_creation.generation.linkedin.InferenceManager"
    ) as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_linkedin_response)

        generator = LinkedInPostGenerator(api_key="test_api_key", prompt_dir=prompt_dir)
        post = generator.generate(None, sample_brief)

    assert post.source_links == [sample_brief.source_url]


def test_generate_linkedin_source_reference_preserved(
    sample_brief, valid_linkedin_response, prompt_dir
):
    """5. Test that generated source reference is preserved."""
    with patch(
        "content_creation.generation.linkedin.InferenceManager"
    ) as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_linkedin_response)

        generator = LinkedInPostGenerator(api_key="test_api_key", prompt_dir=prompt_dir)
        post = generator.generate(None, sample_brief)

    assert post.source_reference == "Paper: Attention Is All You Need"


def test_generate_linkedin_hashtag_validation(sample_brief, prompt_dir):
    """6. Test that hashtag count follows 3 to 5 item contract."""
    # Too few hashtags (2) should fail validation and fall back to needs_review
    invalid_response_few = json.dumps(
        {
            "hook": "hook",
            "post_body": "body",
            "takeaway": "takeaway",
            "cta": "cta",
            "hashtags": ["#AI", "#ML"],
            "source_reference": "ref",
            "claims_used": ["claim"],
            "review_status": "draft",
        }
    )

    # Too many hashtags (6) should also fail
    invalid_response_many = json.dumps(
        {
            "hook": "hook",
            "post_body": "body",
            "takeaway": "takeaway",
            "cta": "cta",
            "hashtags": ["#1", "#2", "#3", "#4", "#5", "#6"],
            "source_reference": "ref",
            "claims_used": ["claim"],
            "review_status": "draft",
        }
    )

    with patch(
        "content_creation.generation.linkedin.InferenceManager"
    ) as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr

        # Test few hashtags fallback
        mock_mgr.generate.return_value = _make_inference_result(invalid_response_few)
        generator = LinkedInPostGenerator(api_key="test_api_key", prompt_dir=prompt_dir)
        post = generator.generate(None, sample_brief)
        assert post.review_status == ReviewStatus.NEEDS_REVIEW
        assert post.hook == "needs_review"

        # Test many hashtags fallback
        mock_mgr.generate.return_value = _make_inference_result(invalid_response_many)
        post = generator.generate(None, sample_brief)
        assert post.review_status == ReviewStatus.NEEDS_REVIEW
        assert post.hook == "needs_review"


def test_linkedin_prompt_registry_resolution():
    """7. Test that prompt registry resolves ("linkedin", "post")."""
    from content_creation.prompts.registry import PromptRegistry

    base_dir = Path("/home/aryan/May-2026/Content-Creation")
    registry = PromptRegistry(base_dir=base_dir)

    resolved_path = registry.get_path("linkedin", "post")
    assert resolved_path == base_dir / "prompts/linkedin_post.md"
