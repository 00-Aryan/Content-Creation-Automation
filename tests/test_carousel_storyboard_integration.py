"""Tests for Storyboard → Carousel integration."""

import json
from unittest.mock import MagicMock, patch

import pytest

from content_creation.domains.storyboard.model import Storyboard
from content_creation.generation.carousel import CarouselGenerator
from content_creation.models.brief import Brief
from content_creation.models.carousel import Carousel
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus


@pytest.fixture
def brief():
    return Brief(
        topic_id="carousel_int_test",
        why_it_matters="Transformers replaced RNNs",
        plain_english_summary=["Brief summary point 1", "Brief summary point 2", "Brief summary point 3"],
        student_takeaway="Learn attention",
        analogy="A librarian scanning books",
        limitation="Quadratic memory",
        audience_fit="ML students",
        recommended_formats=["carousel"],
        source_url="https://example.com/carousel",
        review_status=ReviewStatus.DRAFT,
        generated_at="2026-06-02T00:00:00+00:00",
    )


@pytest.fixture
def storyboard():
    return Storyboard(
        topic_id="carousel_int_test",
        generated_at="2026-06-02T00:00:00+00:00",
        formats_planned=["carousel"],
        script_hook="script-h",
        carousel_hook="Attention is all you need!",
        newsletter_hook="news-h",
        thumbnail_hook="thumb-h",
        script_cta="script-c",
        carousel_cta="Follow us to master LLMs!",
        newsletter_cta="news-c",
        script_claims=["a"],
        carousel_claims=["Storyboard claim A", "Storyboard claim B"],
        newsletter_claims=["c"],
        visual_style="bold_typographic",
        visual_metaphor="A fast parallel scanner vs a sequential card catalog",
    )


@pytest.fixture
def carousel_registry(tmp_path):
    (tmp_path / "prompts").mkdir(exist_ok=True)
    (tmp_path / "prompts" / "carousel.md").write_text("Test carousel prompt {{ brief.topic_id }}")
    return PromptRegistry(tmp_path)


@pytest.fixture
def valid_carousel_response():
    return json.dumps({
        "slides": [
            {
                "slide_number": 1,
                "title": "LLM Generated Title",
                "body": "LLM generated body text",
                "visual_note": "LLM generated visual note",
            }
        ],
        "cta_slide": "LLM Generated CTA",
        "claims_used": ["LLM Generated Claims"],
        "review_status": "draft",
    })


def _make_result(text, success=True):
    from content_creation.inference.providers.base import InferenceResult
    return InferenceResult(
        text=text, provider="gemini", model="gemini-2.5-flash",
        retries=0, duration_seconds=1.0, success=success,
        error=None if success else "error",
    )


class TestCarouselLegacyMode:
    """Verify legacy behavior is unchanged when storyboard=None."""

    def test_legacy_mode_no_storyboard(self, brief, valid_carousel_response, carousel_registry):
        with patch("content_creation.generation.carousel.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_carousel_response)

            gen = CarouselGenerator(api_key="test", prompt_dir=carousel_registry)
            carousel = gen.generate(None, brief)

        assert carousel.slides[0].title == "LLM Generated Title"
        assert carousel.cta_slide == "LLM Generated CTA"
        assert carousel.claims_used == ["LLM Generated Claims"]
        assert carousel.source_links == [brief.source_url]

    def test_legacy_fallback_no_storyboard(self, brief, carousel_registry):
        with patch("content_creation.generation.carousel.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result("", success=False)

            gen = CarouselGenerator(api_key="test", prompt_dir=carousel_registry)
            carousel = gen.generate(None, brief)

        assert carousel.slides[0].title == "needs_review"
        assert carousel.cta_slide == "needs_review"
        assert carousel.claims_used == ["needs_review"]


class TestCarouselStoryboardMode:
    """Verify Storyboard values override LLM-generated fields."""

    def test_storyboard_overrides_fields(self, brief, storyboard, valid_carousel_response, carousel_registry):
        with patch("content_creation.generation.carousel.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_carousel_response)

            gen = CarouselGenerator(api_key="test", prompt_dir=carousel_registry)
            carousel = gen.generate(storyboard, brief)

        # Hook overrides slide 1 title
        assert carousel.slides[0].title == "Attention is all you need!"
        # CTA slide is overridden
        assert carousel.cta_slide == "Follow us to master LLMs!"
        # Claims used are overridden
        assert carousel.claims_used == ["Storyboard claim A", "Storyboard claim B"]

    def test_storyboard_preserves_body_and_visual_notes(self, brief, storyboard, valid_carousel_response, carousel_registry):
        with patch("content_creation.generation.carousel.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_carousel_response)

            gen = CarouselGenerator(api_key="test", prompt_dir=carousel_registry)
            carousel = gen.generate(storyboard, brief)

        # Body and visual note remain LLM-generated (Carousel-owned)
        assert carousel.slides[0].body == "LLM generated body text"
        assert carousel.slides[0].visual_note == "LLM generated visual note"

    def test_storyboard_fallback_uses_storyboard_values(self, brief, storyboard, carousel_registry):
        with patch("content_creation.generation.carousel.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result("", success=False)

            gen = CarouselGenerator(api_key="test", prompt_dir=carousel_registry)
            carousel = gen.generate(storyboard, brief)

        # Fallback fields are populated from storyboard
        assert carousel.slides[0].title == "Attention is all you need!"
        assert carousel.slides[0].visual_note == "A fast parallel scanner vs a sequential card catalog"
        assert carousel.cta_slide == "Follow us to master LLMs!"
        assert carousel.claims_used == ["Storyboard claim A", "Storyboard claim B"]
        assert carousel.review_status == ReviewStatus.NEEDS_REVIEW


class TestCarouselMigration:
    """Verify Phase 5B template mapping and input behavior."""

    def test_prompt_field_mapping(self, brief, storyboard, valid_carousel_response, tmp_path):
        """Verify that brief.analogy is replaced with storyboard.visual_metaphor and summary bullets are from storyboard claims."""
        prompt_dir = tmp_path / "custom_prompts"
        prompt_dir.mkdir(exist_ok=True)
        (prompt_dir / "carousel.md").write_text("Metaphor: {{ brief.analogy }}\nClaims:\n{{ brief.plain_english_summary }}")

        with patch("content_creation.generation.carousel.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_carousel_response)

            gen = CarouselGenerator(api_key="test", prompt_dir=prompt_dir)
            gen.generate(storyboard, brief)

            called_prompt = mock_mgr.generate.call_args[1]["prompt"]
            assert "Metaphor: A fast parallel scanner vs a sequential card catalog" in called_prompt
            assert "- Storyboard claim A\n- Storyboard claim B" in called_prompt
