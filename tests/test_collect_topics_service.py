from unittest.mock import MagicMock, patch

from content_creation.application import ApplicationContext, CollectResult, CollectTopicsService
from content_creation.models.topic import TopicItem


def test_collect_topics_service_orchestration(tmp_path):
    """Test that CollectTopicsService properly loads configs and runs the engine."""
    ctx = ApplicationContext.create(tmp_path)

    test_item = TopicItem(
        id="test-id-1",
        title="Ingested Topic Title",
        url="https://example.com/topic-1",
        source="arxiv",
        published_at="2026-06-02T12:00:00Z",
        author="John Doe",
        raw_text="Canonical topic content representation.",
        status="staged",
    )

    service = CollectTopicsService()

    with patch(
        "content_creation.application.collect_topics_service.load_yaml_config"
    ) as mock_load_yaml, patch(
        "content_creation.application.collect_topics_service.IngestionEngine"
    ) as mock_engine_cls:

        mock_config = {"feeds": [{"id": "arxiv-feed", "source": "arxiv"}]}
        mock_load_yaml.return_value = mock_config

        mock_engine = MagicMock()
        mock_engine.run.return_value = [test_item]
        mock_engine_cls.return_value = mock_engine

        result = service.run(ctx, source_filter="arxiv")

        assert isinstance(result, CollectResult)
        assert result.count == 1
        assert result.new_items == [test_item]

        # Verify orchestration calls
        mock_load_yaml.assert_called_once_with(ctx.feeds_config_path)
        mock_engine_cls.assert_called_once_with(mock_config, ctx.storage)
        mock_engine.run.assert_called_once_with(source_filter="arxiv")
