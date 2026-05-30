"""Tests for Content Intelligence domain."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from content_creation.domains.content_intelligence import (
    ContentIntelligence,
    ContentIntelligenceGenerator,
    ContentIntelligenceRepository,
    ContrastPair,
    EmotionalRegister,
    Hook,
    TopicType,
)
from content_creation.models.brief import Brief
from content_creation.models.topic import TopicCategory
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus


@pytest.fixture
def sample_brief():
    return Brief(
        topic_id="abc123",
        why_it_matters="Transformers replaced RNNs for sequence modeling",
        plain_english_summary=[
            "Attention mechanism processes all tokens in parallel",
            "No recurrence needed, enabling massive parallelization",
            "Scaled to billions of parameters in modern LLMs",
        ],
        student_takeaway="Understand why attention beats recurrence for long sequences",
        analogy="A librarian scanning all books simultaneously instead of reading one by one",
        limitation="Quadratic memory cost with sequence length",
        audience_fit="ML students familiar with basic neural networks",
        recommended_formats=["short_video", "carousel"],
        source_url="https://arxiv.org/abs/1706.03762",
        review_status=ReviewStatus.DRAFT,
        generated_at="2026-05-30T10:00:00+00:00",
    )


@pytest.fixture
def valid_ci_response():
    return json.dumps({
        "primary_hook": {
            "hook_text": "What if reading every book at once was faster than reading them in order?",
            "hook_type": "question",
            "source_field": "analogy",
        },
        "secondary_hook": {
            "hook_text": "Transformers killed recurrence — and nobody looked back.",
            "hook_type": "bold_claim",
            "source_field": "why_it_matters",
        },
        "story_angle": "The death of sequential processing and the rise of parallel attention",
        "curiosity_gap": "Why is processing everything at once better than processing in order?",
        "contrast_pair": {
            "before": "RNNs process tokens one by one, creating bottlenecks",
            "after": "Transformers process all tokens simultaneously via attention",
        },
        "emotional_register": "surprise",
    })


@pytest.fixture
def ci_registry(tmp_path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "content_intelligence.md").write_text("Test prompt {{ brief.topic_id }}")
    return PromptRegistry(tmp_path)


def _make_result(text, success=True):
    from content_creation.inference.providers.base import InferenceResult
    return InferenceResult(
        text=text, provider="gemini", model="gemini-2.5-flash",
        retries=0, duration_seconds=1.0, success=success,
        error=None if success else "error",
    )


# --- Model Tests ---

class TestContentIntelligenceModel:
    def test_create_valid(self):
        ci = ContentIntelligence(
            topic_id="test123",
            generated_at="2026-05-30T10:00:00+00:00",
            topic_type=TopicType.PAPER,
            timeliness_hook="Published this week",
            primary_hook=Hook(hook_text="Why?", hook_type="question", source_field="why_it_matters"),
            secondary_hook=Hook(hook_text="X is dead.", hook_type="bold_claim", source_field="limitation"),
            story_angle="The paradigm shift",
            curiosity_gap="How does it work?",
            contrast_pair=ContrastPair(before="old way", after="new way"),
            emotional_register=EmotionalRegister.SURPRISE,
        )
        assert ci.topic_id == "test123"
        assert ci.topic_type == TopicType.PAPER
        assert ci.emotional_register == EmotionalRegister.SURPRISE

    def test_serialization_roundtrip(self):
        ci = ContentIntelligence(
            topic_id="rt_test",
            generated_at="2026-05-30T10:00:00+00:00",
            topic_type=TopicType.TOOL,
            timeliness_hook="",
            primary_hook=Hook(hook_text="h1", hook_type="statistic", source_field="plain_english_summary"),
            secondary_hook=Hook(hook_text="h2", hook_type="contrast", source_field="limitation"),
            story_angle="angle",
            curiosity_gap="gap",
            contrast_pair=ContrastPair(before="b", after="a"),
            emotional_register=EmotionalRegister.CLARITY,
        )
        data = json.loads(ci.model_dump_json())
        restored = ContentIntelligence(**data)
        assert restored == ci


# --- Generator Tests ---

class TestContentIntelligenceGenerator:
    def test_generate_success(self, sample_brief, valid_ci_response, ci_registry):
        with patch("content_creation.domains.content_intelligence.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_ci_response)

            gen = ContentIntelligenceGenerator(api_key="test", registry=ci_registry)
            ci = gen.generate(sample_brief, topic_category=TopicCategory.PAPER)

        assert ci.topic_id == "abc123"
        assert ci.topic_type == TopicType.PAPER
        assert ci.primary_hook.hook_type == "question"
        assert ci.secondary_hook.hook_type == "bold_claim"
        assert ci.emotional_register == EmotionalRegister.SURPRISE
        assert ci.review_status == ReviewStatus.DRAFT

    def test_generate_fallback_on_failure(self, sample_brief, ci_registry):
        with patch("content_creation.domains.content_intelligence.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result("", success=False)

            gen = ContentIntelligenceGenerator(api_key="test", registry=ci_registry)
            ci = gen.generate(sample_brief)

        assert ci.review_status == ReviewStatus.NEEDS_REVIEW
        assert ci.primary_hook.hook_text == "needs_review"
        assert ci.topic_type == TopicType.UNKNOWN

    def test_generate_fallback_on_malformed_json(self, sample_brief, ci_registry):
        with patch("content_creation.domains.content_intelligence.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result("not json at all")

            gen = ContentIntelligenceGenerator(api_key="test", registry=ci_registry)
            ci = gen.generate(sample_brief, topic_category=TopicCategory.CONCEPT)

        assert ci.review_status == ReviewStatus.NEEDS_REVIEW
        assert ci.topic_type == TopicType.CONCEPT

    def test_deterministic_topic_type_mapping(self, sample_brief, valid_ci_response, ci_registry):
        with patch("content_creation.domains.content_intelligence.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_ci_response)

            gen = ContentIntelligenceGenerator(api_key="test", registry=ci_registry)

            for cat, expected in [
                (TopicCategory.PAPER, TopicType.PAPER),
                (TopicCategory.TOOL, TopicType.TOOL),
                (TopicCategory.NEWS, TopicType.NEWS),
                (TopicCategory.REPO, TopicType.REPO),
            ]:
                ci = gen.generate(sample_brief, topic_category=cat)
                assert ci.topic_type == expected

    def test_timeliness_hook_recent(self, sample_brief, valid_ci_response, ci_registry):
        recent = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        with patch("content_creation.domains.content_intelligence.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_ci_response)

            gen = ContentIntelligenceGenerator(api_key="test", registry=ci_registry)
            ci = gen.generate(sample_brief, published_at=recent)

        assert ci.timeliness_hook == "Published this week"

    def test_timeliness_hook_old(self, sample_brief, valid_ci_response, ci_registry):
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        with patch("content_creation.domains.content_intelligence.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_ci_response)

            gen = ContentIntelligenceGenerator(api_key="test", registry=ci_registry)
            ci = gen.generate(sample_brief, published_at=old)

        assert ci.timeliness_hook == ""


# --- Repository Tests ---

class TestContentIntelligenceRepository:
    def test_save_and_get(self, tmp_path):
        repo = ContentIntelligenceRepository(tmp_path / "ci")
        ci = ContentIntelligence(
            topic_id="repo_test",
            generated_at="2026-05-30T10:00:00+00:00",
            topic_type=TopicType.PAPER,
            timeliness_hook="",
            primary_hook=Hook(hook_text="h1", hook_type="question", source_field="why_it_matters"),
            secondary_hook=Hook(hook_text="h2", hook_type="bold_claim", source_field="limitation"),
            story_angle="angle",
            curiosity_gap="gap",
            contrast_pair=ContrastPair(before="b", after="a"),
            emotional_register=EmotionalRegister.AWE,
        )
        repo.save(ci)
        loaded = repo.get("repo_test")
        assert loaded == ci

    def test_list_all(self, tmp_path):
        repo = ContentIntelligenceRepository(tmp_path / "ci")
        for i in range(3):
            ci = ContentIntelligence(
                topic_id=f"topic_{i}",
                generated_at="2026-05-30T10:00:00+00:00",
                topic_type=TopicType.CONCEPT,
                timeliness_hook="",
                primary_hook=Hook(hook_text="h", hook_type="question", source_field="x"),
                secondary_hook=Hook(hook_text="h2", hook_type="contrast", source_field="y"),
                story_angle="a",
                curiosity_gap="g",
                contrast_pair=ContrastPair(before="b", after="a"),
                emotional_register=EmotionalRegister.CLARITY,
            )
            repo.save(ci)
        assert len(repo.list_all()) == 3

    def test_exists(self, tmp_path):
        repo = ContentIntelligenceRepository(tmp_path / "ci")
        assert not repo.exists("nope")
        ci = ContentIntelligence(
            topic_id="exists_test",
            generated_at="2026-05-30T10:00:00+00:00",
            topic_type=TopicType.TOOL,
            timeliness_hook="Published this week",
            primary_hook=Hook(hook_text="h", hook_type="statistic", source_field="x"),
            secondary_hook=Hook(hook_text="h2", hook_type="question", source_field="y"),
            story_angle="a",
            curiosity_gap="g",
            contrast_pair=ContrastPair(before="b", after="a"),
            emotional_register=EmotionalRegister.EXCITEMENT,
        )
        repo.save(ci)
        assert repo.exists("exists_test")


# --- Quality Evaluation Tests ---

from content_creation.domains.content_intelligence import QualityStatus, evaluate_brief_quality


class TestQualityEvaluation:
    def _make_brief(self, **overrides):
        defaults = dict(
            topic_id="quality_test",
            why_it_matters="Important because X",
            plain_english_summary=["Point 1", "Point 2", "Point 3"],
            student_takeaway="Learn Y",
            analogy="Like Z",
            limitation="Cannot do W",
            audience_fit="ML students",
            recommended_formats=["short_video"],
            source_url="https://example.com",
            review_status=ReviewStatus.DRAFT,
            generated_at="2026-05-30T10:00:00+00:00",
        )
        defaults.update(overrides)
        return Brief(**defaults)

    def test_ready_when_all_fields_present(self):
        brief = self._make_brief()
        assert evaluate_brief_quality(brief) == QualityStatus.READY

    def test_degraded_when_analogy_missing(self):
        brief = self._make_brief(analogy="needs_review")
        assert evaluate_brief_quality(brief) == QualityStatus.DEGRADED

    def test_degraded_when_limitation_missing(self):
        brief = self._make_brief(limitation="needs_review")
        assert evaluate_brief_quality(brief) == QualityStatus.DEGRADED

    def test_degraded_when_multiple_optional_missing(self):
        brief = self._make_brief(analogy="needs_review", limitation="needs_review", audience_fit="needs_review")
        assert evaluate_brief_quality(brief) == QualityStatus.DEGRADED

    def test_blocked_when_why_it_matters_missing(self):
        brief = self._make_brief(why_it_matters="needs_review")
        assert evaluate_brief_quality(brief) == QualityStatus.BLOCKED

    def test_blocked_when_summary_has_needs_review(self):
        brief = self._make_brief(plain_english_summary=["needs_review", "needs_review", "needs_review"])
        assert evaluate_brief_quality(brief) == QualityStatus.BLOCKED

    def test_blocked_when_student_takeaway_missing(self):
        brief = self._make_brief(student_takeaway="needs_review")
        assert evaluate_brief_quality(brief) == QualityStatus.BLOCKED


class TestGeneratorQualityGate:
    def test_blocked_brief_returns_immediately_without_llm_call(self, ci_registry):
        """When Brief is BLOCKED, generator should NOT call inference."""
        brief = Brief(
            topic_id="blocked_test",
            why_it_matters="needs_review",
            plain_english_summary=["needs_review", "needs_review", "needs_review"],
            student_takeaway="needs_review",
            analogy="needs_review",
            limitation="needs_review",
            audience_fit="needs_review",
            recommended_formats=["short_video"],
            source_url="https://example.com",
            review_status=ReviewStatus.NEEDS_REVIEW,
            generated_at="2026-05-30T10:00:00+00:00",
        )
        with patch("content_creation.domains.content_intelligence.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr

            gen = ContentIntelligenceGenerator(api_key="test", registry=ci_registry)
            ci = gen.generate(brief)

        # Inference should NOT have been called
        mock_mgr.generate.assert_not_called()
        assert ci.review_status == ReviewStatus.NEEDS_REVIEW
        assert ci.quality_status == QualityStatus.BLOCKED
        assert ci.primary_hook.hook_text == "needs_review"

    def test_degraded_brief_still_generates(self, sample_brief, valid_ci_response, ci_registry):
        """Degraded briefs should still attempt generation."""
        # sample_brief has all fields present, make it degraded
        sample_brief.analogy = "needs_review"
        sample_brief.limitation = "needs_review"

        with patch("content_creation.domains.content_intelligence.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_ci_response)

            gen = ContentIntelligenceGenerator(api_key="test", registry=ci_registry)
            ci = gen.generate(sample_brief)

        mock_mgr.generate.assert_called_once()
        assert ci.quality_status == QualityStatus.DEGRADED
        assert ci.review_status == ReviewStatus.DRAFT

    def test_ready_brief_generates_with_ready_status(self, sample_brief, valid_ci_response, ci_registry):
        """Fully ready briefs get quality_status=READY."""
        with patch("content_creation.domains.content_intelligence.generator.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_ci_response)

            gen = ContentIntelligenceGenerator(api_key="test", registry=ci_registry)
            ci = gen.generate(sample_brief)

        assert ci.quality_status == QualityStatus.READY


class TestBackwardCompatibility:
    def test_model_loads_without_quality_status(self):
        """Existing stored CI without quality_status should still load."""
        data = {
            "topic_id": "compat_test",
            "generated_at": "2026-05-30T10:00:00+00:00",
            "review_status": "draft",
            "topic_type": "paper",
            "timeliness_hook": "",
            "primary_hook": {"hook_text": "h1", "hook_type": "question", "source_field": "why_it_matters"},
            "secondary_hook": {"hook_text": "h2", "hook_type": "bold_claim", "source_field": "limitation"},
            "story_angle": "angle",
            "curiosity_gap": "gap",
            "contrast_pair": {"before": "b", "after": "a"},
            "emotional_register": "clarity",
        }
        ci = ContentIntelligence(**data)
        assert ci.quality_status is None
        assert ci.topic_type == TopicType.PAPER
