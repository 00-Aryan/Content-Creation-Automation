"""Tests for Storyboard → Thumbnail integration."""

import json
from unittest.mock import MagicMock, patch

import pytest

from content_creation.domains.storyboard.model import Storyboard
from content_creation.generation.thumbnail import ThumbnailGenerator
from content_creation.models.brief import Brief
from content_creation.models.thumbnail import ThumbnailPrompt
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus


@pytest.fixture
def brief():
    return Brief(
        topic_id="thumb_int_test",
        why_it_matters="Transformers replaced RNNs",
        plain_english_summary=["Point 1", "Point 2", "Point 3"],
        student_takeaway="Learn attention",
        analogy="A librarian scanning books",
        limitation="Quadratic memory",
        audience_fit="ML students",
        recommended_formats=["short_video"],
        source_url="https://example.com",
        review_status=ReviewStatus.DRAFT,
        generated_at="2026-05-31T00:00:00+00:00",
    )


@pytest.fixture
def storyboard():
    return Storyboard(
        topic_id="thumb_int_test",
        generated_at="2026-05-31T00:00:00+00:00",
        formats_planned=["short_video", "carousel"],
        script_hook="h1",
        carousel_hook="h2",
        newsletter_hook="h3",
        thumbnail_hook="Attention Replaced Recurrence Forever",
        script_cta="c1",
        carousel_cta="c2",
        newsletter_cta="c3",
        script_claims=["a"],
        carousel_claims=["b"],
        newsletter_claims=["c"],
        visual_style="diagram_overlay",
        visual_metaphor="A librarian scanning all books at once",
    )


@pytest.fixture
def thumb_registry(tmp_path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "thumbnail.md").write_text("Test prompt {{ brief.topic_id }}")
    return PromptRegistry(tmp_path)


@pytest.fixture
def valid_thumb_response():
    return json.dumps({
        "title_text": "LLM Generated Title",
        "supporting_text": "The paper that changed NLP",
        "visual_metaphor": "LLM generated metaphor",
        "style": "clean_minimal",
        "negative_prompt": ["neon brains", "glowing robots", "circuit board heads", "generic cityscape", "matrix code"],
        "readability_notes": "Dark background, white text, left-aligned",
        "review_status": "draft",
    })


def _make_result(text, success=True):
    from content_creation.inference.providers.base import InferenceResult
    return InferenceResult(
        text=text, provider="gemini", model="gemini-2.5-flash",
        retries=0, duration_seconds=1.0, success=success,
        error=None if success else "error",
    )


class TestThumbnailLegacyMode:
    """Verify existing behavior is unchanged when storyboard=None."""

    def test_legacy_mode_no_storyboard(self, brief, valid_thumb_response, thumb_registry):
        with patch("content_creation.generation.thumbnail.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_thumb_response)

            gen = ThumbnailGenerator(api_key="test", prompt_dir=thumb_registry)
            thumb = gen.generate(brief)

        assert thumb.title_text == "LLM Generated Title"
        assert thumb.style == "clean_minimal"
        assert thumb.visual_metaphor == "LLM generated metaphor"
        assert thumb.supporting_text == "The paper that changed NLP"

    def test_legacy_fallback_no_storyboard(self, brief, thumb_registry):
        with patch("content_creation.generation.thumbnail.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result("", success=False)

            gen = ThumbnailGenerator(api_key="test", prompt_dir=thumb_registry)
            thumb = gen.generate(brief)

        assert thumb.title_text == "needs_review"
        assert thumb.style == "clean_minimal"
        assert thumb.visual_metaphor == "needs_review"


class TestThumbnailStoryboardMode:
    """Verify Storyboard values override LLM-generated fields."""

    def test_storyboard_overrides_title_text(self, brief, storyboard, valid_thumb_response, thumb_registry):
        with patch("content_creation.generation.thumbnail.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_thumb_response)

            gen = ThumbnailGenerator(api_key="test", prompt_dir=thumb_registry)
            thumb = gen.generate(brief, storyboard=storyboard)

        assert thumb.title_text == "Attention Replaced Recurrence Forever"

    def test_storyboard_overrides_style(self, brief, storyboard, valid_thumb_response, thumb_registry):
        with patch("content_creation.generation.thumbnail.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_thumb_response)

            gen = ThumbnailGenerator(api_key="test", prompt_dir=thumb_registry)
            thumb = gen.generate(brief, storyboard=storyboard)

        # LLM returned "clean_minimal" but Storyboard says "diagram_overlay"
        assert thumb.style == "diagram_overlay"

    def test_storyboard_overrides_visual_metaphor(self, brief, storyboard, valid_thumb_response, thumb_registry):
        with patch("content_creation.generation.thumbnail.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_thumb_response)

            gen = ThumbnailGenerator(api_key="test", prompt_dir=thumb_registry)
            thumb = gen.generate(brief, storyboard=storyboard)

        assert thumb.visual_metaphor == "A librarian scanning all books at once"

    def test_storyboard_preserves_thumbnail_owned_fields(self, brief, storyboard, valid_thumb_response, thumb_registry):
        with patch("content_creation.generation.thumbnail.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_thumb_response)

            gen = ThumbnailGenerator(api_key="test", prompt_dir=thumb_registry)
            thumb = gen.generate(brief, storyboard=storyboard)

        # These remain LLM-generated (Thumbnail-owned)
        assert thumb.supporting_text == "The paper that changed NLP"
        assert thumb.negative_prompt == ["neon brains", "glowing robots", "circuit board heads", "generic cityscape", "matrix code"]
        assert thumb.readability_notes == "Dark background, white text, left-aligned"

    def test_storyboard_fallback_uses_storyboard_values(self, brief, storyboard, thumb_registry):
        with patch("content_creation.generation.thumbnail.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result("", success=False)

            gen = ThumbnailGenerator(api_key="test", prompt_dir=thumb_registry)
            thumb = gen.generate(brief, storyboard=storyboard)

        # Even on failure, Storyboard-owned fields are populated
        assert thumb.title_text == "Attention Replaced Recurrence Forever"
        assert thumb.style == "diagram_overlay"
        assert thumb.visual_metaphor == "A librarian scanning all books at once"
        # Thumbnail-owned fields fall back to needs_review
        assert thumb.supporting_text == "needs_review"
        assert thumb.review_status == ReviewStatus.NEEDS_REVIEW


class TestThumbnailMigration:
    """Focus tests for Phase 5A ThumbnailGenerator interface migration."""

    def test_new_signature_success(self, brief, storyboard, valid_thumb_response, thumb_registry):
        """Verify calling with (storyboard, brief) works and returns overridden fields."""
        with patch("content_creation.generation.thumbnail.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_thumb_response)

            gen = ThumbnailGenerator(api_key="test", prompt_dir=thumb_registry)
            thumb = gen.generate(storyboard, brief)

        assert isinstance(thumb, ThumbnailPrompt)
        assert thumb.title_text == "Attention Replaced Recurrence Forever"
        assert thumb.style == "diagram_overlay"
        assert thumb.visual_metaphor == "A librarian scanning all books at once"

    def test_missing_brief_raises_value_error(self, storyboard, thumb_registry):
        """Verify that calling generate with storyboard but no brief raises ValueError."""
        gen = ThumbnailGenerator(api_key="test", prompt_dir=thumb_registry)
        with pytest.raises(ValueError, match="Supporting brief context is required"):
            gen.generate(storyboard)

    def test_prompt_field_mapping(self, brief, storyboard, valid_thumb_response, tmp_path):
        """Verify that {{ brief.analogy }} is replaced with storyboard.visual_metaphor in the prompt."""
        # Setup specific template
        prompt_dir = tmp_path / "custom_prompts"
        prompt_dir.mkdir(exist_ok=True)
        (prompt_dir / "thumbnail.md").write_text("Metaphor: {{ brief.analogy }}")

        with patch("content_creation.generation.thumbnail.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_thumb_response)

            gen = ThumbnailGenerator(api_key="test", prompt_dir=prompt_dir)
            gen.generate(storyboard, brief)

            # Assert generator called with updated prompt containing storyboard visual metaphor
            called_prompt = mock_mgr.generate.call_args[1]["prompt"]
            assert called_prompt == "Metaphor: A librarian scanning all books at once"

