"""Tests for Storyboard domain."""

import json
from unittest.mock import MagicMock, patch

import pytest

from content_creation.domains.content_intelligence.model import (
    ContentIntelligence,
    ContrastPair,
    EmotionalRegister,
    Hook,
    TopicType,
)
from content_creation.domains.storyboard import Storyboard, StoryboardGenerator, StoryboardRepository
from content_creation.models.brief import Brief
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus


@pytest.fixture
def sample_brief():
    return Brief(
        topic_id="sb_test_123",
        why_it_matters="Transformers replaced RNNs",
        plain_english_summary=[
            "Attention processes all tokens in parallel",
            "No recurrence needed for sequence modeling",
            "Scales to billions of parameters",
        ],
        student_takeaway="Understand why attention beats recurrence",
        analogy="A librarian scanning all books simultaneously",
        limitation="Quadratic memory cost",
        audience_fit="ML students",
        recommended_formats=["short_video", "carousel", "newsletter"],
        source_url="https://arxiv.org/abs/1706.03762",
        review_status=ReviewStatus.DRAFT,
        generated_at="2026-05-31T00:00:00+00:00",
    )


@pytest.fixture
def sample_ci():
    return ContentIntelligence(
        topic_id="sb_test_123",
        generated_at="2026-05-31T00:00:00+00:00",
        review_status=ReviewStatus.DRAFT,
        topic_type=TopicType.PAPER,
        timeliness_hook="Published this week",
        primary_hook=Hook(hook_text="What if reading every book at once was faster?", hook_type="question", source_field="analogy"),
        secondary_hook=Hook(hook_text="Transformers killed recurrence.", hook_type="bold_claim", source_field="why_it_matters"),
        story_angle="The death of sequential processing",
        curiosity_gap="Why is parallel processing better than sequential?",
        contrast_pair=ContrastPair(before="RNNs process one token at a time", after="Transformers process all tokens simultaneously"),
        emotional_register=EmotionalRegister.SURPRISE,
    )


@pytest.fixture
def valid_storyboard_response():
    return json.dumps({
        "thumbnail_hook": "Attention Replaced Recurrence Forever",
        "script_cta": "Swipe through the carousel for the visual breakdown",
        "carousel_cta": "Subscribe to the newsletter for the deep-dive",
        "newsletter_cta": "Watch the 60-second video summary",
        "script_claims": ["Attention processes all tokens in parallel"],
        "carousel_claims": ["No recurrence needed for sequence modeling", "Scales to billions of parameters"],
        "newsletter_claims": ["Attention processes all tokens in parallel", "Scales to billions of parameters"],
    })


@pytest.fixture
def sb_registry(tmp_path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "storyboard.md").write_text(
        "Test {{ ci.primary_hook }} {{ ci.story_angle }} {{ formats_planned }} {{ brief.claims }}"
    )
    return PromptRegistry(tmp_path)


def _make_result(text, success=True):
    from content_creation.inference.providers.base import InferenceResult
    return InferenceResult(
        text=text, provider="gemini", model="gemini-2.5-flash",
        retries=0, duration_seconds=1.0, success=success,
        error=None if success else "error",
    )


# --- Model Tests ---

class TestStoryboardModel:
    def test_create_valid(self):
        sb = Storyboard(
            topic_id="t1",
            generated_at="2026-05-31T00:00:00+00:00",
            formats_planned=["short_video", "carousel"],
            script_hook="Hook A",
            carousel_hook="Hook B",
            newsletter_hook="Hook C",
            thumbnail_hook="Six Words Max Here",
            script_cta="See the carousel",
            carousel_cta="Read the newsletter",
            newsletter_cta="Watch the video",
            script_claims=["claim1"],
            carousel_claims=["claim2"],
            newsletter_claims=["claim3"],
            visual_style="diagram_overlay",
            visual_metaphor="A librarian scanning books",
        )
        assert sb.topic_id == "t1"
        assert sb.visual_style == "diagram_overlay"

    def test_serialization_roundtrip(self):
        sb = Storyboard(
            topic_id="rt",
            generated_at="2026-05-31T00:00:00+00:00",
            formats_planned=["short_video"],
            script_hook="h1",
            carousel_hook="h2",
            newsletter_hook="h3",
            thumbnail_hook="h4",
            script_cta="c1",
            carousel_cta="c2",
            newsletter_cta="c3",
            script_claims=["a"],
            carousel_claims=["b"],
            newsletter_claims=["c"],
            visual_style="clean_minimal",
            visual_metaphor="metaphor",
        )
        data = json.loads(sb.model_dump_json())
        restored = Storyboard(**data)
        assert restored == sb


# --- Generator Tests ---

class TestStoryboardGenerator:
    def test_generate_success(self, sample_brief, sample_ci, valid_storyboard_response, sb_registry):
        with patch("content_creation.domains.storyboard.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_storyboard_response)

            gen = StoryboardGenerator(api_key="test", registry=sb_registry)
            sb = gen.generate(sample_brief, sample_ci)

        assert sb.topic_id == "sb_test_123"
        assert sb.review_status == ReviewStatus.DRAFT
        assert sb.thumbnail_hook == "Attention Replaced Recurrence Forever"
        assert sb.script_hook == "What if reading every book at once was faster?"
        assert sb.carousel_hook == "Transformers killed recurrence."
        assert sb.newsletter_hook == "Why is parallel processing better than sequential?"
        assert sb.visual_style == "diagram_overlay"
        assert sb.visual_metaphor == "A librarian scanning all books simultaneously"
        assert sb.formats_planned == ["carousel", "newsletter", "short_video"]

    def test_generate_fallback_on_failure(self, sample_brief, sample_ci, sb_registry):
        with patch("content_creation.domains.storyboard.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result("", success=False)

            gen = StoryboardGenerator(api_key="test", registry=sb_registry)
            sb = gen.generate(sample_brief, sample_ci)

        assert sb.review_status == ReviewStatus.NEEDS_REVIEW
        assert sb.thumbnail_hook == "needs_review"
        assert sb.script_cta == "needs_review"
        # Deterministic fields still populated
        assert sb.visual_style == "diagram_overlay"
        assert sb.script_hook == "What if reading every book at once was faster?"

    def test_deterministic_visual_style(self, sample_brief, sample_ci, valid_storyboard_response, sb_registry):
        with patch("content_creation.domains.storyboard.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_storyboard_response)

            gen = StoryboardGenerator(api_key="test", registry=sb_registry)

            # Paper → diagram_overlay
            sample_ci.topic_type = TopicType.PAPER
            assert gen.generate(sample_brief, sample_ci).visual_style == "diagram_overlay"

            # Tool → bold_typographic
            sample_ci.topic_type = TopicType.TOOL
            assert gen.generate(sample_brief, sample_ci).visual_style == "bold_typographic"

            # Concept → metaphor_illustration
            sample_ci.topic_type = TopicType.CONCEPT
            assert gen.generate(sample_brief, sample_ci).visual_style == "metaphor_illustration"

    def test_visual_metaphor_from_analogy(self, sample_brief, sample_ci, valid_storyboard_response, sb_registry):
        with patch("content_creation.domains.storyboard.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_storyboard_response)

            gen = StoryboardGenerator(api_key="test", registry=sb_registry)
            sb = gen.generate(sample_brief, sample_ci)

        assert sb.visual_metaphor == "A librarian scanning all books simultaneously"

    def test_visual_metaphor_fallback_to_contrast(self, sample_brief, sample_ci, valid_storyboard_response, sb_registry):
        sample_brief.analogy = "needs_review"
        with patch("content_creation.domains.storyboard.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_storyboard_response)

            gen = StoryboardGenerator(api_key="test", registry=sb_registry)
            sb = gen.generate(sample_brief, sample_ci)

        assert sb.visual_metaphor == "RNNs process one token at a time → Transformers process all tokens simultaneously"

    def test_format_normalization(self, sample_brief, sample_ci, valid_storyboard_response, sb_registry):
        sample_brief.recommended_formats = ["Case Study", "Technical Presentation", "newsletter"]
        with patch("content_creation.domains.storyboard.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_storyboard_response)

            gen = StoryboardGenerator(api_key="test", registry=sb_registry)
            sb = gen.generate(sample_brief, sample_ci)

        assert "carousel" in sb.formats_planned
        assert "short_video" in sb.formats_planned
        assert "newsletter" in sb.formats_planned


# --- Repository Tests ---

class TestStoryboardRepository:
    def test_save_and_get(self, tmp_path):
        repo = StoryboardRepository(tmp_path / "storyboards")
        sb = Storyboard(
            topic_id="repo_test",
            generated_at="2026-05-31T00:00:00+00:00",
            formats_planned=["short_video"],
            script_hook="h1",
            carousel_hook="h2",
            newsletter_hook="h3",
            thumbnail_hook="h4",
            script_cta="c1",
            carousel_cta="c2",
            newsletter_cta="c3",
            script_claims=["a"],
            carousel_claims=["b"],
            newsletter_claims=["c"],
            visual_style="clean_minimal",
            visual_metaphor="m",
        )
        repo.save(sb)
        loaded = repo.get("repo_test")
        assert loaded == sb

    def test_list_all(self, tmp_path):
        repo = StoryboardRepository(tmp_path / "storyboards")
        for i in range(3):
            sb = Storyboard(
                topic_id=f"topic_{i}",
                generated_at="2026-05-31T00:00:00+00:00",
                formats_planned=["short_video"],
                script_hook="h",
                carousel_hook="h",
                newsletter_hook="h",
                thumbnail_hook="h",
                script_cta="c",
                carousel_cta="c",
                newsletter_cta="c",
                script_claims=["x"],
                carousel_claims=["x"],
                newsletter_claims=["x"],
                visual_style="clean_minimal",
                visual_metaphor="m",
            )
            repo.save(sb)
        assert len(repo.list_all()) == 3

    def test_exists(self, tmp_path):
        repo = StoryboardRepository(tmp_path / "storyboards")
        assert not repo.exists("nope")
