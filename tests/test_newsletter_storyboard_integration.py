"""Tests for Storyboard → Newsletter integration."""

import json
from unittest.mock import MagicMock, patch

import pytest

from content_creation.domains.storyboard.model import Storyboard
from content_creation.generation.newsletter import NewsletterGenerator
from content_creation.models.brief import Brief
from content_creation.models.newsletter import Newsletter
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus


@pytest.fixture
def brief():
    return Brief(
        topic_id="newsletter_int_test",
        why_it_matters="Transformers replaced RNNs",
        plain_english_summary=["Brief summary point 1", "Brief summary point 2", "Brief summary point 3"],
        student_takeaway="Learn attention",
        analogy="A librarian scanning books",
        limitation="Quadratic memory",
        audience_fit="ML students",
        recommended_formats=["newsletter"],
        source_url="https://example.com/newsletter",
        review_status=ReviewStatus.DRAFT,
        generated_at="2026-06-02T00:00:00+00:00",
    )


@pytest.fixture
def storyboard():
    return Storyboard(
        topic_id="newsletter_int_test",
        generated_at="2026-06-02T00:00:00+00:00",
        formats_planned=["newsletter"],
        script_hook="script-h",
        carousel_hook="carousel-h",
        newsletter_hook="The Attention Revolution in NLP",
        thumbnail_hook="thumb-h",
        script_cta="script-c",
        carousel_cta="carousel-c",
        newsletter_cta="Subscribe to our daily ML deep-dives!",
        script_claims=["a"],
        carousel_claims=["b"],
        newsletter_claims=["Storyboard claim 1", "Storyboard claim 2", "Storyboard claim 3"],
        visual_style="clean_minimal",
        visual_metaphor="A parallel text scanner index compared to sequential reading",
    )


@pytest.fixture
def newsletter_registry(tmp_path):
    (tmp_path / "prompts").mkdir(exist_ok=True)
    (tmp_path / "prompts" / "newsletter.md").write_text("Test newsletter prompt {{ brief.topic_id }}")
    return PromptRegistry(tmp_path)


@pytest.fixture
def valid_newsletter_response():
    return json.dumps({
        "subject_line": "LLM Generated Subject Line",
        "sections": [
            {
                "section_name": "what_happened",
                "content": "LLM generated what_happened content",
            },
            {
                "section_name": "why_it_matters",
                "content": "LLM generated why_it_matters content",
            },
            {
                "section_name": "student_takeaway",
                "content": "LLM generated student_takeaway content",
            }
        ],
        "cta": "LLM Generated CTA",
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


class TestNewsletterLegacyMode:
    """Verify legacy behavior is unchanged when storyboard=None."""

    def test_legacy_mode_no_storyboard(self, brief, valid_newsletter_response, newsletter_registry):
        with patch("content_creation.generation.newsletter.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_newsletter_response)

            gen = NewsletterGenerator(api_key="test", prompt_dir=newsletter_registry)
            newsletter = gen.generate(None, brief)

        assert newsletter.subject_line == "LLM Generated Subject Line"
        assert newsletter.cta == "LLM Generated CTA"
        assert newsletter.claims_used == ["LLM Generated Claims"]
        assert newsletter.source_links == [brief.source_url]

    def test_legacy_fallback_no_storyboard(self, brief, newsletter_registry):
        with patch("content_creation.generation.newsletter.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result("", success=False)

            gen = NewsletterGenerator(api_key="test", prompt_dir=newsletter_registry)
            newsletter = gen.generate(None, brief)

        assert newsletter.subject_line == "needs_review"
        assert newsletter.cta == "needs_review"
        assert newsletter.claims_used == ["needs_review"]


class TestNewsletterStoryboardMode:
    """Verify Storyboard values override LLM-generated fields."""

    def test_storyboard_overrides_fields(self, brief, storyboard, valid_newsletter_response, newsletter_registry):
        with patch("content_creation.generation.newsletter.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_newsletter_response)

            gen = NewsletterGenerator(api_key="test", prompt_dir=newsletter_registry)
            newsletter = gen.generate(storyboard, brief)

        # Subject line, CTA, and claims are overridden
        assert newsletter.subject_line == "The Attention Revolution in NLP"
        assert newsletter.cta == "Subscribe to our daily ML deep-dives!"
        assert newsletter.claims_used == ["Storyboard claim 1", "Storyboard claim 2", "Storyboard claim 3"]

    def test_storyboard_preserves_section_content(self, brief, storyboard, valid_newsletter_response, newsletter_registry):
        with patch("content_creation.generation.newsletter.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_newsletter_response)

            gen = NewsletterGenerator(api_key="test", prompt_dir=newsletter_registry)
            newsletter = gen.generate(storyboard, brief)

        # Section contents remain LLM-generated (Newsletter-owned)
        assert newsletter.sections[0].content == "LLM generated what_happened content"
        assert newsletter.sections[1].content == "LLM generated why_it_matters content"
        assert newsletter.sections[2].content == "LLM generated student_takeaway content"

    def test_storyboard_fallback_uses_storyboard_values(self, brief, storyboard, newsletter_registry):
        with patch("content_creation.generation.newsletter.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result("", success=False)

            gen = NewsletterGenerator(api_key="test", prompt_dir=newsletter_registry)
            newsletter = gen.generate(storyboard, brief)

        # Fallback fields are populated from storyboard
        assert newsletter.subject_line == "The Attention Revolution in NLP"
        assert newsletter.cta == "Subscribe to our daily ML deep-dives!"
        assert newsletter.claims_used == ["Storyboard claim 1", "Storyboard claim 2", "Storyboard claim 3"]
        assert newsletter.sections[0].content == "needs_review"
        assert newsletter.review_status == ReviewStatus.NEEDS_REVIEW


class TestNewsletterMigration:
    """Verify Phase 5C prompt mapping and input behavior."""

    def test_prompt_field_mapping(self, brief, storyboard, valid_newsletter_response, tmp_path):
        """Verify that brief.analogy is replaced with storyboard.visual_metaphor and summary bullets are from storyboard claims."""
        prompt_dir = tmp_path / "custom_prompts"
        prompt_dir.mkdir(exist_ok=True)
        (prompt_dir / "newsletter.md").write_text("Metaphor: {{ brief.analogy }}\nClaims:\n{{ brief.plain_english_summary }}")

        with patch("content_creation.generation.newsletter.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_newsletter_response)

            gen = NewsletterGenerator(api_key="test", prompt_dir=prompt_dir)
            gen.generate(storyboard, brief)

            called_prompt = mock_mgr.generate.call_args[1]["prompt"]
            assert "Metaphor: A parallel text scanner index compared to sequential reading" in called_prompt
            assert "- Storyboard claim 1\n- Storyboard claim 2\n- Storyboard claim 3" in called_prompt
