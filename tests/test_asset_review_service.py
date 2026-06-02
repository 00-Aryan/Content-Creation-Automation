import json
from unittest.mock import MagicMock, patch

from content_creation.application import (
    ApplicationContext,
    AssetDecision,
    AssetReviewService,
    ReviewResult,
)
from content_creation.models.manifest import TopicManifest
from content_creation.shared.enums import ReviewStatus


def test_asset_review_service_orchestration(tmp_path):
    """Test get_review_queue loads assets/summaries and apply_decisions updates status and rebuilds manifest."""
    topic_id = "test-topic-1"

    # Setup manifest file
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / f"{topic_id}.json"

    manifest_data = {
        "topic_id": topic_id,
        "topic_title": "Title From Manifest",
        "source_url": "https://example.com/source",
        "assets": {
            "brief": {"status": "needs_review", "path": "brief_path"},
            "script": {"status": "missing"},
        },
    }
    with open(manifest_file, "w") as f:
        json.dump(manifest_data, f)

    # Setup brief file
    brief_dir = tmp_path / "briefs"
    brief_dir.mkdir(parents=True, exist_ok=True)
    brief_file = brief_dir / f"{topic_id}.json"

    brief_data = {
        "topic_id": topic_id,
        "why_it_matters": "Matters because of unit test summary",
    }
    with open(brief_file, "w") as f:
        json.dump(brief_data, f)

    service = AssetReviewService()

    # Mock storage properties pointing to tmp_path structures
    mock_storage = MagicMock()
    mock_storage.manifests_dir = manifest_dir
    mock_storage.briefs_dir = brief_dir
    mock_storage.scripts_dir = tmp_path / "scripts"
    mock_storage.carousels_dir = tmp_path / "carousels"
    mock_storage.newsletters_dir = tmp_path / "newsletters"
    mock_storage.thumbnails_dir = tmp_path / "thumbnails"

    ctx = MagicMock(storage=mock_storage)

    # 1. Verify get_review_queue
    queue = service.get_review_queue(ctx, topic_id)
    assert len(queue) == 1
    assert queue[0].asset_type == "brief"
    assert queue[0].status == "needs_review"
    assert queue[0].summary_text == "Matters because of unit test summary"
    assert queue[0].content == brief_data

    # 2. Verify apply_decisions
    decisions = [AssetDecision(asset_type="brief", status=ReviewStatus.APPROVED)]
    mock_manifest_obj = MagicMock(spec=TopicManifest)

    with patch(
        "content_creation.application.asset_review_service.ManifestBuilder"
    ) as mock_builder_cls:
        mock_builder = MagicMock()
        mock_builder.build.return_value = mock_manifest_obj
        mock_builder_cls.return_value = mock_builder

        mock_storage.update_asset_status.return_value = True
        mock_storage.get_scored.return_value = None

        result = service.apply_decisions(ctx, topic_id, decisions)

        assert isinstance(result, ReviewResult)
        assert result.approved_count == 1
        assert result.rejected_count == 0
        assert result.manifest == mock_manifest_obj

        # Verify backend writes and compilations
        mock_storage.update_asset_status.assert_called_once_with(
            "brief", topic_id, ReviewStatus.APPROVED
        )
        mock_builder.build.assert_called_once_with(
            topic_id=topic_id,
            topic_title="Title From Manifest",
            source_url="https://example.com/source",
        )
        mock_storage.save_manifest.assert_called_once_with(mock_manifest_obj)
