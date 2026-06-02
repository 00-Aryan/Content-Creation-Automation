"""Tests for ContentIntelligenceService orchestration."""

from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

from content_creation.application.context import ApplicationContext
from content_creation.application.content_intelligence_service import (
    ContentIntelligenceFailure,
    ContentIntelligenceGenerationResult,
    ContentIntelligenceService,
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


@pytest.fixture
def sample_brief():
    return Brief(
        topic_id="test-topic-1",
        why_it_matters="Matters because test",
        plain_english_summary=["Summary 1", "Summary 2"],
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
        author="John Doe",
        raw_text="Canonical topic content representation.",
        status="scored",
        priority_score=9.5,
        scoring_details={"relevance": 9.0, "novelty": 10.0},
        validation_flags=[],
    )


@pytest.fixture
def mock_ci():
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


def test_content_intelligence_service_success(tmp_path, sample_brief, sample_scored_item, mock_ci):
    """Test successful orchestration of ContentIntelligenceService."""
    service = ContentIntelligenceService()
    
    with patch(
        "content_creation.application.content_intelligence_service.ContentIntelligenceGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
        mock_generator.generate.return_value = mock_ci
        mock_gen_cls.return_value = mock_generator

        # Mock dependencies
        mock_storage = MagicMock()
        mock_storage.list_briefs.return_value = [sample_brief]
        mock_storage.get_scored.return_value = sample_scored_item
        mock_storage.content_intelligence_dir = tmp_path
        
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

        assert isinstance(result, ContentIntelligenceGenerationResult)
        assert result.generated_count == 1
        assert result.skipped_count == 0
        assert len(result.failures) == 0
        assert result.content_intelligences == [mock_ci]

        # Verify calls
        mock_storage.list_briefs.assert_called_once()
        mock_storage.get_scored.assert_called_once_with("test-topic-1")
        mock_generator.generate.assert_called_once_with(
            brief=sample_brief,
            topic_category=TopicCategory.PAPER,
            published_at="2026-06-02T12:00:00Z",
        )
        mock_storage.save_content_intelligence.assert_called_once_with(mock_ci)
        mock_workflow.mark_completed.assert_called_once_with(
            topic_id="test-topic-1",
            stage="content_intelligence",
            artifact_path=str(tmp_path / "test-topic-1.json"),
        )


def test_content_intelligence_service_skip_workflow(tmp_path, sample_brief, sample_scored_item):
    """Test that the service skips generation if workflow marks it completed."""
    service = ContentIntelligenceService()

    with patch(
        "content_creation.application.content_intelligence_service.ContentIntelligenceGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
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

        assert result.generated_count == 0
        assert result.skipped_count == 1
        assert len(result.failures) == 0
        assert len(result.content_intelligences) == 0

        # Generator should not be called
        mock_generator.generate.assert_not_called()
        mock_storage.save_content_intelligence.assert_not_called()


def test_content_intelligence_service_skip_existing_file(tmp_path, sample_brief, sample_scored_item):
    """Test that the service skips generation if the file already exists on disk."""
    service = ContentIntelligenceService()

    # Pre-create the file to trigger skip
    ci_file = tmp_path / "test-topic-1.json"
    ci_file.write_text("{}")

    with patch(
        "content_creation.application.content_intelligence_service.ContentIntelligenceGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
        mock_gen_cls.return_value = mock_generator

        mock_storage = MagicMock()
        mock_storage.list_briefs.return_value = [sample_brief]
        mock_storage.get_scored.return_value = sample_scored_item
        mock_storage.content_intelligence_dir = tmp_path

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
        assert len(result.content_intelligences) == 0

        mock_generator.generate.assert_not_called()
        mock_storage.save_content_intelligence.assert_not_called()


def test_content_intelligence_service_generation_failure(tmp_path, sample_brief, sample_scored_item):
    """Test that generation failures are caught at the topic boundary and recorded."""
    service = ContentIntelligenceService()

    with patch(
        "content_creation.application.content_intelligence_service.ContentIntelligenceGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
        mock_generator.generate.side_effect = RuntimeError("LLM Failure")
        mock_gen_cls.return_value = mock_generator

        mock_storage = MagicMock()
        mock_storage.list_briefs.return_value = [sample_brief]
        mock_storage.get_scored.return_value = sample_scored_item
        mock_storage.content_intelligence_dir = tmp_path

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
        assert "LLM Failure" in result.failures[0].error
        assert len(result.content_intelligences) == 0

        # Verify workflow is marked failed
        mock_workflow.mark_failed.assert_called_once_with("test-topic-1", "content_intelligence")
        mock_storage.save_content_intelligence.assert_not_called()


def test_content_intelligence_service_prioritization_and_limit(tmp_path, mock_ci):
    """Test prioritization ordering and top_n limit."""
    briefs = [
        Brief(
            topic_id="topic-low",
            why_it_matters="Matters low",
            plain_english_summary=[],
            student_takeaway="",
            analogy="",
            limitation="",
            audience_fit="",
            recommended_formats=[],
            source_url="https://example.com/low",
            review_status="draft",
            generated_at="2026-06-02T12:00:00Z",
        ),
        Brief(
            topic_id="topic-high",
            why_it_matters="Matters high",
            plain_english_summary=[],
            student_takeaway="",
            analogy="",
            limitation="",
            audience_fit="",
            recommended_formats=[],
            source_url="https://example.com/high",
            review_status="draft",
            generated_at="2026-06-02T12:00:00Z",
        ),
    ]

    scored_items = {
        "topic-low": ScoredTopicItem(
            id="topic-low",
            title="Low priority topic",
            url="https://example.com/low",
            source="arxiv",
            published_at="2026-06-02T12:00:00Z",
            author="John Doe",
            raw_text="",
            status="scored",
            priority_score=3.0,
            scoring_details={},
            validation_flags=[],
        ),
        "topic-high": ScoredTopicItem(
            id="topic-high",
            title="High priority topic",
            url="https://example.com/high",
            source="arxiv",
            published_at="2026-06-02T12:00:00Z",
            author="John Doe",
            raw_text="",
            status="scored",
            priority_score=9.0,
            scoring_details={},
            validation_flags=[],
        ),
    }

    service = ContentIntelligenceService()

    with patch(
        "content_creation.application.content_intelligence_service.ContentIntelligenceGenerator"
    ) as mock_gen_cls:
        mock_generator = MagicMock()
        mock_generator.generate.return_value = mock_ci
        mock_gen_cls.return_value = mock_generator

        mock_storage = MagicMock()
        mock_storage.list_briefs.return_value = briefs
        mock_storage.get_scored.side_effect = lambda x: scored_items.get(x)
        mock_storage.content_intelligence_dir = tmp_path

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

        # Verify that only the high priority item is processed
        assert result.generated_count == 1
        mock_generator.generate.assert_called_once()
        assert mock_generator.generate.call_args[1]["brief"].topic_id == "topic-high"
