"""Tests for script generation module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from content_creation.generation.script import ScriptGenerator
from content_creation.models.brief import Brief, ReviewStatus
from content_creation.models.script import Script, ReviewStatus as ScriptReviewStatus


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
    """Per-format prompt files required by ScriptGenerator."""
    for name in ("short_video", "carousel", "newsletter"):
        (tmp_path / f"{name}.md").write_text("Test prompt")
    return tmp_path


@pytest.fixture
def valid_script_response():
    """Valid JSON response from Gemini for a script."""
    return json.dumps(
        {
            "hook": "What if machines could read entire documents instantly?",
            "script_sections": [
                "Context: Transformers came from a 2017 Google paper",
                "Explanation: Attention lets each word look at every other word",
                "Practical: You can fine-tune BERT for sentiment analysis in hours",
            ],
            "cta": "Try the Google Colab notebook linked in the description",
            "claims_used": [
                "why_it_matters: Transformers revolutionized NLP",
                "plain_english_summary: Transformers use attention",
            ],
            "source_links": ["https://arxiv.org/abs/1706.03762"],
            "review_status": "draft",
        }
    )


@pytest.fixture
def malformed_response():
    """Malformed JSON response from Gemini."""
    return "This is not JSON at all"


def _make_inference_result(text, success=True):
    """Helper to create a mock InferenceResult."""
    from content_creation.inference.providers.base import InferenceResult
    return InferenceResult(
        text=text, provider="gemini", model="gemini-2.5-flash",
        retries=0, duration_seconds=1.0, success=success, error=None if success else "error",
    )


def test_generate_script_success(sample_brief, valid_script_response, prompt_dir):
    """Test successful script generation with valid Gemini response."""
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_script_response)

        generator = ScriptGenerator(api_key="test_api_key", prompt_dir=prompt_dir)
        script = generator.generate(sample_brief, format="short_video")

    assert isinstance(script, Script)
    assert script.topic_id == sample_brief.topic_id
    assert script.format == "short_video"
    assert script.hook == "What if machines could read entire documents instantly?"
    assert len(script.script_sections) == 3
    assert script.cta == "Try the Google Colab notebook linked in the description"
    assert len(script.claims_used) == 2
    assert script.source_links == ["https://arxiv.org/abs/1706.03762"]
    assert script.review_status == ScriptReviewStatus.DRAFT


def test_generate_script_malformed_json_fallback(
    sample_brief, malformed_response, prompt_dir
):
    """Test fallback behavior when inference returns malformed JSON."""
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(malformed_response)

        generator = ScriptGenerator(api_key="test_api_key", prompt_dir=prompt_dir)
        script = generator.generate(sample_brief, format="carousel")

    assert script.hook == "needs_review"
    assert script.script_sections == [
        "needs_review",
        "needs_review",
        "needs_review",
        "needs_review",
    ]
    assert script.review_status == ScriptReviewStatus.NEEDS_REVIEW
    assert script.topic_id == sample_brief.topic_id
    assert script.format == "carousel"


def test_generate_script_429_retry(sample_brief, valid_script_response, prompt_dir):
    """Test that retry is handled by inference layer and result still works."""
    from content_creation.inference.providers.base import InferenceResult

    result_with_retries = InferenceResult(
        text=valid_script_response, provider="gemini", model="gemini-2.5-flash",
        retries=1, duration_seconds=16.0, success=True,
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = result_with_retries

        generator = ScriptGenerator(api_key="test_api_key", prompt_dir=prompt_dir)
        script = generator.generate(sample_brief, format="short_video")

    assert mock_mgr.generate.call_count == 1
    assert script.review_status == ScriptReviewStatus.DRAFT


def test_generate_script_format_passed_through(
    sample_brief, valid_script_response, prompt_dir
):
    """Test that format is correctly passed to Script.format field."""
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_script_response)

        generator = ScriptGenerator(api_key="test_api_key", prompt_dir=prompt_dir)
        script = generator.generate(sample_brief, format="newsletter")

    assert script.format == "newsletter"


def test_generate_script_source_url_injected(
    sample_brief, valid_script_response, prompt_dir
):
    """Test that source_url from brief is injected into source_links."""
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_script_response)

        generator = ScriptGenerator(api_key="test_api_key", prompt_dir=prompt_dir)
        script = generator.generate(sample_brief, format="short_video")

    assert sample_brief.source_url in script.source_links


# CarouselGenerator tests
from content_creation.generation.carousel import CarouselGenerator
from content_creation.models.carousel import Carousel, CarouselSlide


@pytest.fixture
def carousel_prompt_dir(tmp_path):
    """Prompt file required by CarouselGenerator."""
    (tmp_path / "carousel.md").write_text("Test prompt")
    return tmp_path


@pytest.fixture
def valid_carousel_response():
    """Valid JSON response from Gemini for a carousel."""
    return json.dumps(
        {
            "slides": [
                {
                    "slide_number": 1,
                    "title": "Transformers Explained",
                    "body": "A new architecture that changed NLP forever",
                    "visual_note": "Diagram of encoder-decoder structure",
                },
                {
                    "slide_number": 2,
                    "title": "Attention Mechanism",
                    "body": "Lets each word look at all other words",
                    "visual_note": "Attention matrix heatmap",
                },
            ],
            "cta_slide": "Try fine-tuning BERT on your own data",
            "claims_used": [
                "why_it_matters: Transformers revolutionized NLP",
            ],
            "review_status": "draft",
        }
    )


def _make_carousel_result(text, success=True):
    """Helper to create a mock InferenceResult for carousel tests."""
    from content_creation.inference.providers.base import InferenceResult
    return InferenceResult(
        text=text, provider="gemini", model="gemini-2.5-flash",
        retries=0, duration_seconds=1.0, success=success, error=None if success else "error",
    )


def test_generate_carousel_success(sample_brief, valid_carousel_response, carousel_prompt_dir):
    """Test successful carousel generation with valid response."""
    with patch("content_creation.generation.carousel.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_carousel_result(valid_carousel_response)

        generator = CarouselGenerator(api_key="test_api_key", prompt_dir=carousel_prompt_dir)
        carousel = generator.generate(sample_brief)

    assert isinstance(carousel, Carousel)
    assert carousel.topic_id == sample_brief.topic_id
    assert len(carousel.slides) == 2
    assert carousel.slides[0].title == "Transformers Explained"
    assert carousel.cta_slide == "Try fine-tuning BERT on your own data"
    assert carousel.source_links == ["https://arxiv.org/abs/1706.03762"]
    assert carousel.review_status == ScriptReviewStatus.DRAFT


def test_generate_carousel_malformed_json_fallback(sample_brief, malformed_response, carousel_prompt_dir):
    """Test fallback behavior when inference returns malformed JSON."""
    with patch("content_creation.generation.carousel.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_carousel_result(malformed_response)

        generator = CarouselGenerator(api_key="test_api_key", prompt_dir=carousel_prompt_dir)
        carousel = generator.generate(sample_brief)

    assert carousel.slides[0].title == "needs_review"
    assert carousel.cta_slide == "needs_review"
    assert carousel.review_status == ScriptReviewStatus.NEEDS_REVIEW
    assert carousel.topic_id == sample_brief.topic_id


def test_generate_carousel_429_retry(sample_brief, valid_carousel_response, carousel_prompt_dir):
    """Test that retry is handled by inference layer and result still works."""
    from content_creation.inference.providers.base import InferenceResult

    result_with_retries = InferenceResult(
        text=valid_carousel_response, provider="gemini", model="gemini-2.5-flash",
        retries=1, duration_seconds=16.0, success=True,
    )

    with patch("content_creation.generation.carousel.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = result_with_retries

        generator = CarouselGenerator(api_key="test_api_key", prompt_dir=carousel_prompt_dir)
        carousel = generator.generate(sample_brief)

    assert mock_mgr.generate.call_count == 1
    assert carousel.review_status == ScriptReviewStatus.DRAFT


def test_generate_carousel_slides_parsed_correctly(sample_brief, valid_carousel_response, carousel_prompt_dir):
    """Test that slides are parsed into List[CarouselSlide] correctly."""
    with patch("content_creation.generation.carousel.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_carousel_result(valid_carousel_response)

        generator = CarouselGenerator(api_key="test_api_key", prompt_dir=carousel_prompt_dir)
        carousel = generator.generate(sample_brief)

    assert isinstance(carousel.slides[0], CarouselSlide)
    assert carousel.slides[0].slide_number == 1
    assert carousel.slides[0].visual_note == "Diagram of encoder-decoder structure"


# NewsletterGenerator tests
from content_creation.generation.newsletter import NewsletterGenerator
from content_creation.models.newsletter import Newsletter, NewsletterSection


@pytest.fixture
def newsletter_prompt_dir(tmp_path):
    """Prompt file required by NewsletterGenerator."""
    (tmp_path / "newsletter.md").write_text("Test prompt")
    return tmp_path


@pytest.fixture
def valid_newsletter_response():
    """Valid JSON response from Gemini for a newsletter."""
    return json.dumps(
        {
            "subject_line": "Transformers: The New Standard",
            "sections": [
                {
                    "section_name": "what_happened",
                    "content": "Google introduced Transformers in 2017, replacing RNNs for sequence tasks.",
                },
                {
                    "section_name": "why_it_matters",
                    "content": "Transformers achieve state-of-the-art results on translation and language understanding.",
                },
                {
                    "section_name": "student_takeaway",
                    "content": "Start by understanding attention mechanism before moving to BERT and GPT.",
                },
            ],
            "cta": "Try the Google Colab notebook in the link below",
            "claims_used": [
                "why_it_matters: Transformers revolutionized NLP",
            ],
            "review_status": "draft",
        }
    )


def _make_newsletter_result(text, success=True):
    """Helper to create a mock InferenceResult for newsletter tests."""
    from content_creation.inference.providers.base import InferenceResult
    return InferenceResult(
        text=text, provider="gemini", model="gemini-2.5-flash",
        retries=0, duration_seconds=1.0, success=success, error=None if success else "error",
    )


def test_generate_newsletter_success(sample_brief, valid_newsletter_response, newsletter_prompt_dir):
    """Test successful newsletter generation with valid response."""
    with patch("content_creation.generation.newsletter.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_newsletter_result(valid_newsletter_response)

        generator = NewsletterGenerator(api_key="test_api_key", prompt_dir=newsletter_prompt_dir)
        newsletter = generator.generate(sample_brief)

    assert isinstance(newsletter, Newsletter)
    assert newsletter.topic_id == sample_brief.topic_id
    assert newsletter.subject_line == "Transformers: The New Standard"
    assert len(newsletter.sections) == 3
    assert newsletter.sections[0].section_name == "what_happened"
    assert newsletter.cta == "Try the Google Colab notebook in the link below"
    assert newsletter.source_links == ["https://arxiv.org/abs/1706.03762"]
    assert newsletter.review_status == ScriptReviewStatus.DRAFT


def test_generate_newsletter_malformed_json_fallback(sample_brief, malformed_response, newsletter_prompt_dir):
    """Test fallback behavior when inference returns malformed JSON."""
    with patch("content_creation.generation.newsletter.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_newsletter_result(malformed_response)

        generator = NewsletterGenerator(api_key="test_api_key", prompt_dir=newsletter_prompt_dir)
        newsletter = generator.generate(sample_brief)

    assert newsletter.subject_line == "needs_review"
    assert len(newsletter.sections) == 3
    assert newsletter.sections[0].content == "needs_review"
    assert newsletter.review_status == ScriptReviewStatus.NEEDS_REVIEW
    assert newsletter.topic_id == sample_brief.topic_id


def test_generate_newsletter_429_retry(sample_brief, valid_newsletter_response, newsletter_prompt_dir):
    """Test that retry is handled by inference layer and result still works."""
    from content_creation.inference.providers.base import InferenceResult

    result_with_retries = InferenceResult(
        text=valid_newsletter_response, provider="gemini", model="gemini-2.5-flash",
        retries=1, duration_seconds=16.0, success=True,
    )

    with patch("content_creation.generation.newsletter.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = result_with_retries

        generator = NewsletterGenerator(api_key="test_api_key", prompt_dir=newsletter_prompt_dir)
        newsletter = generator.generate(sample_brief)

    assert mock_mgr.generate.call_count == 1
    assert newsletter.review_status == ScriptReviewStatus.DRAFT


def test_generate_newsletter_sections_parsed_correctly(sample_brief, valid_newsletter_response, newsletter_prompt_dir):
    """Test that sections are parsed into List[NewsletterSection] correctly."""
    with patch("content_creation.generation.newsletter.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_newsletter_result(valid_newsletter_response)

        generator = NewsletterGenerator(api_key="test_api_key", prompt_dir=newsletter_prompt_dir)
        newsletter = generator.generate(sample_brief)

    assert isinstance(newsletter.sections[0], NewsletterSection)
    assert newsletter.sections[0].section_name == "what_happened"
    assert newsletter.sections[1].section_name == "why_it_matters"
    assert newsletter.sections[2].section_name == "student_takeaway"


# ThumbnailGenerator tests
from content_creation.generation.thumbnail import ThumbnailGenerator
from content_creation.models.thumbnail import ThumbnailPrompt


@pytest.fixture
def thumbnail_prompt_dir(tmp_path):
    """Prompt file required by ThumbnailGenerator."""
    (tmp_path / "thumbnail.md").write_text("Test prompt")
    return tmp_path


@pytest.fixture
def valid_thumbnail_response():
    """Valid JSON response from Gemini for a thumbnail."""
    return json.dumps(
        {
            "title_text": "Why Attention Changed Everything",
            "supporting_text": "The 2017 paper that redefined NLP",
            "visual_metaphor": "a librarian scanning every book simultaneously instead of reading them in order",
            "style": "diagram_overlay",
            "negative_prompt": [
                "neon brains",
                "glowing robots",
                "circuit board heads",
                "generic futuristic cityscape",
                "matrix-style falling code",
                "transformer architecture diagrams"
            ],
            "readability_notes": "Dark background with white text, keep left third clear for title overlay, avoid busy patterns",
            "review_status": "draft",
        }
    )


def _make_thumbnail_result(text, success=True):
    """Helper to create a mock InferenceResult for thumbnail tests."""
    from content_creation.inference.providers.base import InferenceResult
    return InferenceResult(
        text=text, provider="gemini", model="gemini-2.5-flash",
        retries=0, duration_seconds=1.0, success=success, error=None if success else "error",
    )


def test_generate_thumbnail_success(sample_brief, valid_thumbnail_response, thumbnail_prompt_dir):
    """Test successful thumbnail generation with valid response."""
    with patch("content_creation.generation.thumbnail.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_thumbnail_result(valid_thumbnail_response)

        generator = ThumbnailGenerator(api_key="test_api_key", prompt_dir=thumbnail_prompt_dir)
        thumbnail = generator.generate(sample_brief)

    assert isinstance(thumbnail, ThumbnailPrompt)
    assert thumbnail.topic_id == sample_brief.topic_id
    assert thumbnail.title_text == "Why Attention Changed Everything"
    assert thumbnail.supporting_text == "The 2017 paper that redefined NLP"
    assert thumbnail.visual_metaphor == "a librarian scanning every book simultaneously instead of reading them in order"
    assert thumbnail.style == "diagram_overlay"
    assert len(thumbnail.negative_prompt) == 6
    assert "neon brains" in thumbnail.negative_prompt
    assert thumbnail.readability_notes == "Dark background with white text, keep left third clear for title overlay, avoid busy patterns"
    assert thumbnail.review_status == ScriptReviewStatus.DRAFT


def test_generate_thumbnail_malformed_json_fallback(sample_brief, malformed_response, thumbnail_prompt_dir):
    """Test fallback behavior when inference returns malformed JSON."""
    with patch("content_creation.generation.thumbnail.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_thumbnail_result(malformed_response)

        generator = ThumbnailGenerator(api_key="test_api_key", prompt_dir=thumbnail_prompt_dir)
        thumbnail = generator.generate(sample_brief)

    assert thumbnail.title_text == "needs_review"
    assert thumbnail.supporting_text == "needs_review"
    assert thumbnail.visual_metaphor == "needs_review"
    assert thumbnail.style == "clean_minimal"
    assert thumbnail.negative_prompt == ["needs_review"]
    assert thumbnail.readability_notes == "needs_review"
    assert thumbnail.review_status == ScriptReviewStatus.NEEDS_REVIEW
    assert thumbnail.topic_id == sample_brief.topic_id


def test_generate_thumbnail_429_retry(sample_brief, valid_thumbnail_response, thumbnail_prompt_dir):
    """Test that retry is handled by inference layer and result still works."""
    from content_creation.inference.providers.base import InferenceResult

    result_with_retries = InferenceResult(
        text=valid_thumbnail_response, provider="gemini", model="gemini-2.5-flash",
        retries=1, duration_seconds=16.0, success=True,
    )

    with patch("content_creation.generation.thumbnail.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = result_with_retries

        generator = ThumbnailGenerator(api_key="test_api_key", prompt_dir=thumbnail_prompt_dir)
        thumbnail = generator.generate(sample_brief)

    assert mock_mgr.generate.call_count == 1
    assert thumbnail.review_status == ScriptReviewStatus.DRAFT


def test_generate_thumbnail_negative_prompt_as_list(sample_brief, valid_thumbnail_response, thumbnail_prompt_dir):
    """Test that negative_prompt is correctly parsed as List[str]."""
    with patch("content_creation.generation.thumbnail.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_thumbnail_result(valid_thumbnail_response)

        generator = ThumbnailGenerator(api_key="test_api_key", prompt_dir=thumbnail_prompt_dir)
        thumbnail = generator.generate(sample_brief)

    assert isinstance(thumbnail.negative_prompt, list)
    assert all(isinstance(item, str) for item in thumbnail.negative_prompt)
    assert len(thumbnail.negative_prompt) == 6
