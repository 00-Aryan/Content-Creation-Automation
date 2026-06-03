"""Unit and integration tests for Phase 7.2 remediation (findings VF-001 and VF-002)."""

from unittest.mock import MagicMock, patch
import pytest

from content_creation.application import ApplicationContext
from content_creation.application.content_intelligence_service import ContentIntelligenceService
from content_creation.application.storyboard_service import StoryboardService
from content_creation.application.asset_generation_service import AssetGenerationService
from content_creation.models.brief import Brief
from content_creation.domains.content_intelligence import ContentIntelligence
from content_creation.domains.storyboard import Storyboard
from content_creation.shared.enums import ReviewStatus


@pytest.fixture
def sample_brief():
    return Brief(
        topic_id="test-topic-1",
        why_it_matters="Matters because test",
        plain_english_summary=["Summary 1", "Summary 2", "Summary 3"],
        student_takeaway="Takeaway",
        analogy="Analogy",
        limitation="Limit",
        audience_fit="Fit",
        recommended_formats=["short_video"],
        source_url="https://example.com/topic-1",
        review_status="draft",
        generated_at="2026-06-02T12:00:00Z",
    )


@pytest.fixture
def sample_scored_item():
    from content_creation.models.topic import ScoredTopicItem, TopicCategory, TopicStatus
    return ScoredTopicItem(
        id="test-topic-1",
        title="Ingested Topic Title",
        url="https://example.com/topic-1",
        source="arxiv",
        published_at="2026-06-03T00:00:00Z",
        author="Validation",
        raw_text="Fixture raw text",
        excerpt="Fixture excerpt",
        category=TopicCategory.PAPER,
        topic_tags=["test"],
        status=TopicStatus.SCORED,
        metadata={"recommended_formats": ["short_video"]},
        priority_score=95.0,
        scoring_details={"fixture": 95.0},
        validation_flags=[],
    )


@pytest.fixture
def sample_ci():
    from content_creation.domains.content_intelligence import Hook, TopicType, ContrastPair, EmotionalRegister
    return ContentIntelligence(
        topic_id="test-topic-1",
        generated_at="2026-06-02T12:00:00Z",
        review_status=ReviewStatus.DRAFT,
        quality_status="ready",
        topic_type=TopicType.PAPER,
        timeliness_hook="hook",
        primary_hook=Hook(hook_text="text", hook_type="question", source_field="why_it_matters"),
        secondary_hook=Hook(hook_text="text2", hook_type="bold_claim", source_field="limitation"),
        story_angle="angle",
        curiosity_gap="gap",
        contrast_pair=ContrastPair(before="before", after="after"),
        emotional_register=EmotionalRegister.SURPRISE,
    )


def test_ci_service_divergence_regeneration(tmp_path, sample_brief, sample_scored_item, sample_ci):
    """VF-001: CI stage is marked completed but artifact file does not exist.

    Expected: Divergence is detected and generation runs to regenerate the artifact.
    """
    service = ContentIntelligenceService()

    with patch(
        "content_creation.application.content_intelligence_service.ContentIntelligenceGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
        mock_generator.generate.return_value = sample_ci
        mock_gen_cls.return_value = mock_generator

        mock_storage = MagicMock()
        mock_storage.list_briefs.return_value = [sample_brief]
        mock_storage.get_scored.return_value = sample_scored_item
        mock_storage.content_intelligence_dir = tmp_path

        mock_workflow = MagicMock()
        mock_workflow.stage_completed.return_value = True

        ctx = MagicMock(
            storage=mock_storage,
            workflow=mock_workflow,
            prompt_registry=MagicMock(),
        )

        result = service.run(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=0.0
        )

        # Regeneration occurs (generated_count == 1, skipped_count == 0)
        assert result.generated_count == 1
        assert result.skipped_count == 0
        mock_generator.generate.assert_called_once()
        mock_storage.save_content_intelligence.assert_called_once()


def test_storyboard_service_divergence_regeneration(tmp_path, sample_scored_item, sample_ci):
    """VF-001: Storyboard stage is marked completed but artifact file does not exist.

    Expected: Divergence is detected and generation runs to regenerate the storyboard.
    """
    service = StoryboardService()

    with patch(
        "content_creation.application.storyboard_service.StoryboardGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
        mock_storyboard = Storyboard(
            topic_id="test-topic-1",
            generated_at="2026-06-02T12:00:00Z",
            review_status=ReviewStatus.DRAFT,
            formats_planned=["short_video"],
            script_hook="hook",
            carousel_hook="carousel_hook",
            newsletter_hook="newsletter_hook",
            thumbnail_hook="thumbnail_hook",
            script_cta="cta",
            carousel_cta="carousel_cta",
            newsletter_cta="newsletter_cta",
            script_claims=["claim"],
            carousel_claims=["carousel_claim"],
            newsletter_claims=["newsletter_claim"],
            visual_style="diagram_overlay",
            visual_metaphor="metaphor",
        )
        mock_generator.generate.return_value = mock_storyboard
        mock_gen_cls.return_value = mock_generator

        mock_storage = MagicMock()
        mock_storage.list_content_intelligence.return_value = [sample_ci]
        mock_storage.get_scored.return_value = sample_scored_item
        mock_storage.storyboards_dir = tmp_path

        mock_workflow = MagicMock()
        mock_workflow.stage_completed.return_value = True

        ctx = MagicMock(
            storage=mock_storage,
            workflow=mock_workflow,
            prompt_registry=MagicMock(),
        )

        result = service.run(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=0.0
        )

        # Regeneration occurs
        assert result.generated_count == 1
        assert result.skipped_count == 0
        mock_generator.generate.assert_called_once()
        mock_storage.save_storyboard.assert_called_once()


def test_asset_generation_service_divergence_regeneration(tmp_path, sample_brief):
    """VF-001: Asset stage is marked completed but artifact files do not exist.

    Expected: Divergence is detected and generation runs to regenerate assets.
    """
    service = AssetGenerationService()

    with patch(
        "content_creation.application.asset_generation_service.ThumbnailGenerator"
    ) as mock_thumb_cls, patch(
        "content_creation.application.asset_generation_service.ScriptGenerator"
    ) as mock_script_cls:
        mock_thumb = MagicMock()
        mock_thumb_cls.return_value = mock_thumb
        mock_script = MagicMock()
        mock_script_cls.return_value = mock_script

        mock_storage = MagicMock()
        mock_storage.list_briefs.return_value = [sample_brief]
        mock_storyboard = Storyboard(
            topic_id="test-topic-1",
            generated_at="2026-06-02T12:00:00Z",
            review_status=ReviewStatus.DRAFT,
            formats_planned=["short_video"],
            script_hook="hook",
            carousel_hook="carousel_hook",
            newsletter_hook="newsletter_hook",
            thumbnail_hook="thumbnail_hook",
            script_cta="cta",
            carousel_cta="carousel_cta",
            newsletter_cta="newsletter_cta",
            script_claims=["claim"],
            carousel_claims=["carousel_claim"],
            newsletter_claims=["newsletter_claim"],
            visual_style="diagram_overlay",
            visual_metaphor="metaphor",
        )
        mock_storage.get_storyboard.return_value = mock_storyboard
        mock_storage.thumbnails_dir = tmp_path / "thumbnails"
        mock_storage.scripts_dir = tmp_path / "scripts"

        mock_workflow = MagicMock()
        mock_workflow.stage_completed.return_value = True

        ctx = MagicMock(
            storage=mock_storage,
            workflow=mock_workflow,
            prompt_registry=MagicMock(),
        )

        result = service.run(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=0.0
        )

        # Regeneration occurs (no skips)
        assert result.counts["thumbnail"] == 1
        assert result.counts["script"] == 1
        assert result.skipped_count == 0
        mock_thumb.generate.assert_called_once()
        mock_script.generate.assert_called_once()


def test_asset_generation_service_storyboard_missing_failure(tmp_path, sample_brief):
    """VF-002: Storyboard artifact is missing (None) during asset generation.

    Expected: AssetGenerationService raises a ValueError and halts execution.
    """
    service = AssetGenerationService()

    mock_storage = MagicMock()
    mock_storage.list_briefs.return_value = [sample_brief]
    mock_storage.get_storyboard.return_value = None  # Missing storyboard!

    mock_workflow = MagicMock()

    ctx = MagicMock(
        storage=mock_storage,
        workflow=mock_workflow,
        prompt_registry=MagicMock(),
    )

    with pytest.raises(ValueError) as exc_info:
        service.run(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=0.0
        )

    assert "Required Storyboard artifact is missing" in str(exc_info.value)
