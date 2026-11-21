"""Headless Streamlit AppTest suite covering all UI pages, fragments, and corruption resilience."""

import json
import os
from pathlib import Path
from typing import Any, Dict
import pytest
from streamlit.testing.v1 import AppTest

from content_creation.ui.services.client import get_context, get_notification_db, get_sse_infrastructure


def _make_brief_dict(topic_id: str) -> Dict[str, Any]:
    return {
        "topic_id": topic_id,
        "why_it_matters": "Why it matters explanation",
        "plain_english_summary": ["Point 1", "Point 2", "Point 3"],
        "student_takeaway": "Key takeaway",
        "analogy": "Educational analogy",
        "limitation": "Technical limitation",
        "audience_fit": "Students and researchers",
        "recommended_formats": ["script", "carousel", "newsletter"],
        "source_url": "https://example.com/research",
        "generated_at": "2026-11-21T00:00:00Z",
    }


def _make_manifest_dict(topic_id: str) -> Dict[str, Any]:
    return {
        "topic_id": topic_id,
        "topic_title": f"Topic Title {topic_id}",
        "source_url": "https://example.com/research",
        "assets": {},
        "overall_status": "partial",
        "blocking_reasons": [],
        "ready_for_planner": False,
        "generated_at": "2026-11-21T00:00:00Z",
    }


@pytest.fixture(autouse=True)
def setup_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Isolate workspace and reset Streamlit cached resources."""
    from content_creation.ui.services.client import (
        get_context,
        get_notification_db,
        get_sse_infrastructure,
    )
    get_context.clear()
    get_notification_db.clear()
    get_sse_infrastructure.clear()
    monkeypatch.setenv("CONTENT_FACTORY_ROOT", str(tmp_path))
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "briefs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "storyboards").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "manifests").mkdir(parents=True, exist_ok=True)
    yield tmp_path
    get_context.clear()
    get_notification_db.clear()
    get_sse_infrastructure.clear()


@pytest.mark.parametrize(
    "page_file",
    [
        "src/content_creation/ui/app.py",
        "src/content_creation/ui/pages/1_topic_collection.py",
        "src/content_creation/ui/pages/2_topic_pipeline.py",
        "src/content_creation/ui/pages/3_brief_viewer.py",
        "src/content_creation/ui/pages/4_storyboard.py",
        "src/content_creation/ui/pages/5_asset_workshop.py",
        "src/content_creation/ui/pages/6_operations_dashboard.py",
    ],
)
def test_all_pages_render_without_exceptions(page_file: str) -> None:
    """Gate 5: Verify all 7 Streamlit pages execute with 0 exceptions."""
    at = AppTest.from_file(page_file, default_timeout=15)
    at.run()
    assert len(at.exception) == 0, f"Page {page_file} crashed: {at.exception}"


def test_storyboard_page_handles_corrupt_artifact_gracefully(tmp_path: Path) -> None:
    """UI-001 / ERR-006: Verify 4_storyboard.py detects corrupt/0-byte storyboard files without crash."""
    topic_id = "topic-corrupt-sb"
    brief_file = tmp_path / "data" / "briefs" / f"{topic_id}.json"
    brief_file.write_text(json.dumps(_make_brief_dict(topic_id)), encoding="utf-8")

    # Create a 0-byte corrupted storyboard file on disk
    corrupt_sb_file = tmp_path / "data" / "storyboards" / f"{topic_id}.json"
    corrupt_sb_file.write_bytes(b"")

    at = AppTest.from_file("src/content_creation/ui/pages/4_storyboard.py", default_timeout=15)
    at.run()

    assert len(at.exception) == 0, f"Page crashed with: {at.exception}"

    # Verify warning about corrupted/0-byte file appears
    warnings = [w.value for w in at.warning]
    assert any("corrupted or empty (0-byte)" in w for w in warnings), f"Expected corruption warning in {warnings}"


def test_storyboard_page_displays_missing_when_no_file(tmp_path: Path) -> None:
    """Verify 4_storyboard.py shows 'not yet generated' when file does not exist."""
    topic_id = "topic-missing-sb"
    brief_file = tmp_path / "data" / "briefs" / f"{topic_id}.json"
    brief_file.write_text(json.dumps(_make_brief_dict(topic_id)), encoding="utf-8")

    at = AppTest.from_file("src/content_creation/ui/pages/4_storyboard.py", default_timeout=15)
    at.run()

    assert len(at.exception) == 0, f"Page crashed with: {at.exception}"

    infos = [i.value for i in at.info]
    assert any("not yet generated" in i for i in infos), f"Expected missing info in {infos}"


def test_asset_workshop_handles_corrupt_storyboard(tmp_path: Path) -> None:
    """Verify 5_asset_workshop.py handles corrupt storyboard without unhandled crash."""
    topic_id = "topic-corrupt-sb-asset"
    (tmp_path / "data" / "briefs" / f"{topic_id}.json").write_text(
        json.dumps(_make_brief_dict(topic_id)), encoding="utf-8"
    )
    (tmp_path / "data" / "manifests" / f"{topic_id}.json").write_text(
        json.dumps(_make_manifest_dict(topic_id)), encoding="utf-8"
    )

    # Seed 0-byte storyboard
    (tmp_path / "data" / "storyboards" / f"{topic_id}.json").write_bytes(b"")

    at = AppTest.from_file("src/content_creation/ui/pages/5_asset_workshop.py", default_timeout=15)
    at.run()

    assert len(at.exception) == 0, f"Page crashed with: {at.exception}"
    warnings = [w.value for w in at.warning]
    assert any("corrupted or empty (0-byte)" in w for w in warnings), f"Expected corruption warning in {warnings}"
