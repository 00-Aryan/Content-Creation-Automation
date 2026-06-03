"""Tests for StoryboardService orchestration."""

from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

from content_creation.application.context import ApplicationContext
from content_creation.application.storyboard_service import (
    StoryboardFailure,
    StoryboardGenerationResult,
    StoryboardService,
)
from content_creation.models.brief import Brief
from content_creation.models.topic import ScoredTopicItem, TopicCategory
from content_creation.domains.content_intelligence import (
    ContentIntelligence,
    Hook,
    ContrastPair,
    EmotionalRegister,
    TopicType,
)
from content_creation.domains.storyboard import Storyboard


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
    return ScoredTopicItem(
        id="test-topic-1",
        title="Ingested Topic Title",
        url="https://example.com/topic-1",
        source="arxiv",
        published_at="2026-06-02T12:00:00Z",
        category=TopicCategory.PAPER,
        author="John Doe",
        raw_text="Canonical topic content representation.",
        status="scored",
        priority_score=9.5,
        scoring_details={"relevance": 9.0, "novelty": 10.0},
        validation_flags=[],
    )


@pytest.fixture
def sample_ci():
    return ContentIntelligence(
        topic_id="test-topic-1",
        generated_at="2026-06-02T12:00:00Z",
        topic_type=TopicType.PAPER,
        timeliness_hook="Published this week",
        primary_hook=Hook(hook_text="Why?", hook_type="question", source_field="why_it_matters"),
        secondary_hook=Hook(hook_text="X is dead.", hook_type="bold_claim", source_field="limitation"),
        story_angle="Story angle",
        curiosity_gap="Curiosity gap",
        contrast_pair=ContrastPair(before="before", after="after"),
        emotional_register=EmotionalRegister.SURPRISE,
    )


@pytest.fixture
def mock_sb():
    return Storyboard(
        topic_id="test-topic-1",
        generated_at="2026-06-02T12:00:00Z",
        formats_planned=["short_video"],
        script_hook="Why?",
        carousel_hook="X is dead.",
        newsletter_hook="Curiosity gap",
        thumbnail_hook="Six words max",
        script_cta="cta1",
        carousel_cta="cta2",
        newsletter_cta="cta3",
        script_claims=["claim1"],
        carousel_claims=["claim2"],
        newsletter_claims=["claim3"],
        visual_style="clean_minimal",
        visual_metaphor="metaphor",
    )


def test_storyboard_service_success(tmp_path, sample_brief, sample_scored_item, sample_ci, mock_sb):
    """Test successful orchestration of StoryboardService."""
    service = StoryboardService()

    with patch(
        "content_creation.application.storyboard_service.StoryboardGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
        mock_generator.generate.return_value = mock_sb
        mock_gen_cls.return_value = mock_generator

        # Mock storage calls
        mock_storage = MagicMock()
        mock_storage.list_content_intelligence.return_value = [sample_ci]
        mock_storage.get_brief.return_value = sample_brief
        mock_storage.get_scored.return_value = sample_scored_item
        mock_storage.storyboards_dir = tmp_path

        mock_workflow = MagicMock()
        mock_workflow.stage_completed.return_value = False

        ctx = MagicMock(
            storage=mock_storage,
            workflow=mock_workflow,
            prompt_registry=MagicMock(),
        )

        result = service.run(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=0.0
        )

        assert isinstance(result, StoryboardGenerationResult)
        assert result.generated_count == 1
        assert result.skipped_count == 0
        assert len(result.failures) == 0
        assert result.storyboards == [mock_sb]

        # Verify calls
        mock_storage.list_content_intelligence.assert_called_once()
        mock_storage.get_brief.assert_called_once_with("test-topic-1")
        mock_generator.generate.assert_called_once_with(
            brief=sample_brief,
            ci=sample_ci,
        )
        mock_storage.save_storyboard.assert_called_once_with(mock_sb)
        mock_workflow.mark_completed.assert_called_once_with(
            topic_id="test-topic-1",
            stage="storyboard",
            artifact_path=str(tmp_path / "test-topic-1.json"),
        )


def test_storyboard_service_skip_workflow(tmp_path, sample_scored_item, sample_ci):
    """Test that the service skips generation if workflow marks it completed."""
    service = StoryboardService()
    sb_file = tmp_path / "test-topic-1.json"
    sb_file.write_text("{}")

    with patch(
        "content_creation.application.storyboard_service.StoryboardGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
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

        assert result.generated_count == 0
        assert result.skipped_count == 1
        assert len(result.failures) == 0
        assert len(result.storyboards) == 0

        mock_generator.generate.assert_not_called()
        mock_storage.save_storyboard.assert_not_called()


def test_storyboard_service_skip_existing_file(tmp_path, sample_scored_item, sample_ci):
    """Test that the service skips generation if the file already exists on disk."""
    service = StoryboardService()

    sb_file = tmp_path / "test-topic-1.json"
    sb_file.write_text("{}")

    with patch(
        "content_creation.application.storyboard_service.StoryboardGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
        mock_gen_cls.return_value = mock_generator

        mock_storage = MagicMock()
        mock_storage.list_content_intelligence.return_value = [sample_ci]
        mock_storage.get_scored.return_value = sample_scored_item
        mock_storage.storyboards_dir = tmp_path

        mock_workflow = MagicMock()
        mock_workflow.stage_completed.return_value = False

        ctx = MagicMock(
            storage=mock_storage,
            workflow=mock_workflow,
            prompt_registry=MagicMock(),
        )

        result = service.run(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=0.0
        )

        assert result.generated_count == 0
        assert result.skipped_count == 1
        assert len(result.failures) == 0
        assert len(result.storyboards) == 0

        mock_generator.generate.assert_not_called()
        mock_storage.save_storyboard.assert_not_called()


def test_storyboard_service_missing_brief(tmp_path, sample_scored_item, sample_ci):
    """Test handling of missing matching Brief dependency."""
    service = StoryboardService()

    with patch(
        "content_creation.application.storyboard_service.StoryboardGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
        mock_gen_cls.return_value = mock_generator

        mock_storage = MagicMock()
        mock_storage.list_content_intelligence.return_value = [sample_ci]
        # Return None to simulate missing brief
        mock_storage.get_brief.return_value = None
        mock_storage.get_scored.return_value = sample_scored_item
        mock_storage.storyboards_dir = tmp_path

        mock_workflow = MagicMock()
        mock_workflow.stage_completed.return_value = False

        ctx = MagicMock(
            storage=mock_storage,
            workflow=mock_workflow,
            prompt_registry=MagicMock(),
        )

        result = service.run(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=0.0
        )

        assert result.generated_count == 0
        assert result.skipped_count == 0
        assert len(result.failures) == 1
        assert result.failures[0].topic_id == "test-topic-1"
        assert "Missing Brief dependency" in result.failures[0].error
        assert len(result.storyboards) == 0

        # Generator should not run, workflow marked failed
        mock_generator.generate.assert_not_called()
        mock_workflow.mark_failed.assert_called_once_with("test-topic-1", "storyboard")


def test_storyboard_service_generation_failure(tmp_path, sample_brief, sample_scored_item, sample_ci):
    """Test that generator failures are caught and workflow is marked failed."""
    service = StoryboardService()

    with patch(
        "content_creation.application.storyboard_service.StoryboardGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
        mock_generator.generate.side_effect = RuntimeError("Generation error")
        mock_gen_cls.return_value = mock_generator

        mock_storage = MagicMock()
        mock_storage.list_content_intelligence.return_value = [sample_ci]
        mock_storage.get_brief.return_value = sample_brief
        mock_storage.get_scored.return_value = sample_scored_item
        mock_storage.storyboards_dir = tmp_path

        mock_workflow = MagicMock()
        mock_workflow.stage_completed.return_value = False

        ctx = MagicMock(
            storage=mock_storage,
            workflow=mock_workflow,
            prompt_registry=MagicMock(),
        )

        result = service.run(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=0.0
        )

        assert result.generated_count == 0
        assert result.skipped_count == 0
        assert len(result.failures) == 1
        assert result.failures[0].topic_id == "test-topic-1"
        assert "Generation error" in result.failures[0].error
        assert len(result.storyboards) == 0

        mock_workflow.mark_failed.assert_called_once_with("test-topic-1", "storyboard")
        mock_storage.save_storyboard.assert_not_called()


def test_storyboard_service_prioritization(tmp_path, mock_sb):
    """Test prioritization ordering based on scored topic priority."""
    ci_list = [
        ContentIntelligence(
            topic_id="low-pri",
            generated_at="2026-06-02T12:00:00Z",
            topic_type=TopicType.PAPER,
            timeliness_hook="",
            primary_hook=Hook(hook_text="", hook_type="bold_claim", source_field=""),
            secondary_hook=Hook(hook_text="", hook_type="bold_claim", source_field=""),
            story_angle="",
            curiosity_gap="",
            contrast_pair=ContrastPair(before="", after=""),
            emotional_register=EmotionalRegister.CLARITY,
        ),
        ContentIntelligence(
            topic_id="high-pri",
            generated_at="2026-06-02T12:00:00Z",
            topic_type=TopicType.PAPER,
            timeliness_hook="",
            primary_hook=Hook(hook_text="", hook_type="bold_claim", source_field=""),
            secondary_hook=Hook(hook_text="", hook_type="bold_claim", source_field=""),
            story_angle="",
            curiosity_gap="",
            contrast_pair=ContrastPair(before="", after=""),
            emotional_register=EmotionalRegister.CLARITY,
        ),
    ]

    scored_items = {
        "low-pri": ScoredTopicItem(
            id="low-pri",
            title="Low priority topic",
            url="https://example.com/low",
            source="arxiv",
            published_at="2026-06-02T12:00:00Z",
            category=TopicCategory.PAPER,
            author="John Doe",
            raw_text="",
            status="scored",
            priority_score=4.0,
            scoring_details={},
            validation_flags=[],
        ),
        "high-pri": ScoredTopicItem(
            id="high-pri",
            title="High priority topic",
            url="https://example.com/high",
            source="arxiv",
            published_at="2026-06-02T12:00:00Z",
            category=TopicCategory.PAPER,
            author="John Doe",
            raw_text="",
            status="scored",
            priority_score=8.5,
            scoring_details={},
            validation_flags=[],
        ),
    }

    service = StoryboardService()

    with patch(
        "content_creation.application.storyboard_service.StoryboardGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
        mock_generator.generate.return_value = mock_sb
        mock_gen_cls.return_value = mock_generator

        mock_storage = MagicMock()
        mock_storage.list_content_intelligence.return_value = ci_list
        mock_storage.get_brief.side_effect = lambda topic_id: Brief(
            topic_id=topic_id,
            why_it_matters="",
            plain_english_summary=["a", "b", "c"],
            student_takeaway="",
            analogy="",
            limitation="",
            audience_fit="",
            recommended_formats=[],
            source_url="",
            review_status="draft",
            generated_at="",
        )
        mock_storage.get_scored.side_effect = lambda x: scored_items.get(x)
        mock_storage.storyboards_dir = tmp_path

        mock_workflow = MagicMock()
        mock_workflow.stage_completed.return_value = False

        ctx = MagicMock(
            storage=mock_storage,
            workflow=mock_workflow,
            prompt_registry=MagicMock(),
        )

        # Run with top_n = 1
        result = service.run(
            ctx, top_n=1, api_key="dummy_key", rate_limit_delay=0.0
        )

        assert result.generated_count == 1
        mock_generator.generate.assert_called_once()
        # High priority item should be processed
        assert mock_generator.generate.call_args[1]["ci"].topic_id == "high-pri"
