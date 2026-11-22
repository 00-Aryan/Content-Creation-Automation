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


def _make_storyboard_dict(topic_id: str) -> Dict[str, Any]:
    return {
        "topic_id": topic_id,
        "generated_at": "2026-11-21T00:00:00Z",
        "formats_planned": ["short_video", "carousel", "newsletter"],
        "script_hook": f"Attention ML researchers for {topic_id}!",
        "script_cta": "Read the research paper below",
        "script_claims": ["Breakthrough efficiency", "Reduced GPU memory by 50%"],
        "carousel_hook": "How this new algorithm works in 5 slides",
        "carousel_cta": "Follow for daily AI summaries",
        "carousel_claims": ["Breakthrough efficiency"],
        "newsletter_hook": "Welcome to this week's AI research edition",
        "newsletter_cta": "Subscribe for more insights",
        "newsletter_claims": ["Breakthrough efficiency"],
        "thumbnail_hook": "50% GPU Drop",
        "visual_metaphor": "GPU cooling block melting into numbers",
        "visual_style": "clean_minimal",
    }


def _make_newsletter_dict(topic_id: str) -> Dict[str, Any]:
    return {
        "topic_id": topic_id,
        "subject_line": "AI Research Digest: Transformers Breakdown",
        "sections": [
            {"section_name": "what_happened", "content": "Recent advances in transformer architectures..."},
            {"section_name": "why_it_matters", "content": "Memory consumption has been reduced drastically."},
            {"section_name": "student_takeaway", "content": "Attention mechanisms scale efficiently."},
        ],
        "cta": "Read the full research documentation",
        "claims_used": ["Breakthrough efficiency"],
        "source_links": ["https://example.com/research"],
        "review_status": "needs_review",
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
    (tmp_path / "data" / "newsletters").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "thumbnails").mkdir(parents=True, exist_ok=True)
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


def test_storyboard_page_renders_valid_storyboard(tmp_path: Path) -> None:
    """UI-001 / ERR-006: 4_storyboard.py cleanly renders a valid storyboard without warning."""
    topic_id = "topic-valid-sb"
    (tmp_path / "data" / "briefs" / f"{topic_id}.json").write_text(
        json.dumps(_make_brief_dict(topic_id)), encoding="utf-8"
    )
    (tmp_path / "data" / "storyboards" / f"{topic_id}.json").write_text(
        json.dumps(_make_storyboard_dict(topic_id)), encoding="utf-8"
    )

    at = AppTest.from_file("src/content_creation/ui/pages/4_storyboard.py", default_timeout=15)
    at.run()

    assert len(at.exception) == 0, f"Page crashed with: {at.exception}"
    warnings = [w.value for w in at.warning]
    # No corruption warning for a valid storyboard file
    assert not any("corrupted or empty (0-byte)" in w for w in warnings)


def test_asset_workshop_renders_newsletter_tab_cleanly(tmp_path: Path) -> None:
    """UI-001 / Preservation: 5_asset_workshop.py renders secondary format (Newsletter) cleanly."""
    topic_id = "topic-newsletter-test"
    (tmp_path / "data" / "briefs" / f"{topic_id}.json").write_text(
        json.dumps(_make_brief_dict(topic_id)), encoding="utf-8"
    )
    (tmp_path / "data" / "manifests" / f"{topic_id}.json").write_text(
        json.dumps(_make_manifest_dict(topic_id)), encoding="utf-8"
    )
    (tmp_path / "data" / "newsletters" / f"{topic_id}.json").write_text(
        json.dumps(_make_newsletter_dict(topic_id)), encoding="utf-8"
    )

    at = AppTest.from_file("src/content_creation/ui/pages/5_asset_workshop.py", default_timeout=15)
    at.run()

    assert len(at.exception) == 0, f"Page crashed with: {at.exception}"
    # Verify newsletter content rendered
    all_markdown = " ".join(m.value for m in at.markdown)
    assert any("AI Research Digest" in m.value or "Subject Line" in m.value for m in at.markdown)


def test_notification_badge_and_summary_fragments() -> None:
    """UI-004 / ERR-004: Verify notification badge and summary fragments handle states and errors."""
    from unittest.mock import MagicMock
    from content_creation.ui.components.notification_panel import (
        render_notification_badge,
        render_notification_badge_fragment,
        render_notification_summary_fragment,
        render_notification_summary_panel,
    )
    from content_creation.notifications.query import NotificationSummary

    # 1. Badge direct rendering
    render_notification_badge(0)
    render_notification_badge(1)
    render_notification_badge(7)

    # 2. Badge fragment with valid client
    client_mock = MagicMock()
    client_mock.get_notification_unread_count.return_value = 4
    render_notification_badge_fragment(client_mock)

    # 3. Badge fragment with failing client (fallback to 0)
    client_fail = MagicMock()
    client_fail.get_notification_unread_count.side_effect = RuntimeError("DB locked")
    render_notification_badge_fragment(client_fail)

    # 4. Summary panel direct rendering - empty
    svc_empty = MagicMock()
    svc_empty.summary.return_value = NotificationSummary(
        total_unread=0,
        unread_by_category={},
        unread_by_severity={},
        recent_failures=[],
        recent_approvals=[],
        recent_completions=[],
    )
    render_notification_summary_panel(svc_empty)

    # 5. Summary panel direct rendering - populated
    svc_pop = MagicMock()
    svc_pop.summary.return_value = NotificationSummary(
        total_unread=3,
        unread_by_category={"workflow": 2, "review": 1},
        unread_by_severity={"info": 1, "warning": 2},
        recent_failures=[],
        recent_approvals=[],
        recent_completions=[],
    )
    render_notification_summary_panel(svc_pop)

    # 6. Summary fragment with failing service (fallback warning)
    client_summary_fail = MagicMock()
    client_summary_fail.notification_service.summary.side_effect = RuntimeError("Service crashed")
    render_notification_summary_fragment(client_summary_fail)


def test_notification_panel_components_coverage() -> None:
    """UI-004: Exercise row rendering, inline notifications, and notification center."""
    from uuid import uuid4
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from content_creation.ui.components.notification_panel import (
        _render_notification_row,
        render_inline_notification,
        render_notification_center,
        render_notification_summary_panel,
    )
    from content_creation.notifications.models import (
        Notification,
        NotificationSeverity,
        NotificationCategory,
        NotificationStatus,
    )
    from content_creation.notifications.query import (
        NotificationSummary,
        NotificationPage,
    )

    # 1. Inline notifications
    render_inline_notification("Success msg", severity="success")
    render_inline_notification("Warning msg", severity="warning")
    render_inline_notification("Error msg", severity="error")
    render_inline_notification("Info msg", severity="info")

    # 2. Notification rows (read vs unread, with/without actions)
    n_unread = Notification(
        notification_id=uuid4(),
        title="Pipeline Succeeded",
        message="Asset generation completed",
        severity=NotificationSeverity.SUCCESS,
        category=NotificationCategory.WORKFLOW,
        status=NotificationStatus.UNREAD,
        timestamp=datetime.now(timezone.utc),
        correlation_id="c-1",
    )
    n_read = Notification(
        notification_id=uuid4(),
        title="Review Assigned",
        message="Brief requires review",
        severity=NotificationSeverity.WARNING,
        category=NotificationCategory.REVIEW,
        status=NotificationStatus.READ,
        timestamp=datetime.now(timezone.utc),
        correlation_id="c-2",
    )
    mock_service = MagicMock()
    _render_notification_row(n_unread, service=mock_service, show_actions=True)
    _render_notification_row(n_read, service=None, show_actions=False)

    # 3. Notification summary with recent failure, approval, completion
    n_fail = Notification(
        notification_id=uuid4(),
        title="Job Failed",
        message="Quota exceeded",
        severity=NotificationSeverity.ERROR,
        category=NotificationCategory.JOB,
        status=NotificationStatus.UNREAD,
        timestamp=datetime.now(timezone.utc),
        correlation_id="c-3",
    )
    summary_rich = NotificationSummary(
        total_unread=1,
        unread_by_category={"workflow": 1},
        unread_by_severity={"error": 1},
        recent_failures=[n_fail],
        recent_approvals=[n_unread],
        recent_completions=[n_unread],
    )
    mock_service.summary.return_value = summary_rich
    render_notification_summary_panel(mock_service)

    # 4. Notification Center (empty and populated)
    mock_service.query.return_value = NotificationPage(
        notifications=[n_unread, n_read],
        total_count=2,
        page=1,
        page_size=20,
    )
    render_notification_center(mock_service)



def test_operations_dashboard_ast_zero_sqlite_layer_violations() -> None:
    """UI-002 / ERR-020: Verify 6_operations_dashboard.py contains ZERO direct SQLite/store imports."""
    import ast

    dashboard_path = Path("src/content_creation/ui/pages/6_operations_dashboard.py")
    tree = ast.parse(dashboard_path.read_text(encoding="utf-8"))

    forbidden_modules = [
        "sqlite3",
        "content_creation.jobs",
        "content_creation.events.store",
        "content_creation.metrics",
        "content_creation.audit",
        "content_creation.platform.observability",
    ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in forbidden_modules:
                    assert not alias.name.startswith(forbidden), (
                        f"Found prohibited direct import '{alias.name}' in 6_operations_dashboard.py"
                    )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for forbidden in forbidden_modules:
                assert not mod.startswith(forbidden), (
                    f"Found prohibited 'from {mod} import ...' in 6_operations_dashboard.py"
                )


def test_operations_dashboard_snapshot_and_badge_helpers() -> None:
    """UI-002 / ERR-020: Verify operations dashboard snapshot delegation and badge formatting."""
    import importlib
    dash_module = importlib.import_module("content_creation.ui.pages.6_operations_dashboard")
    from content_creation.platform.observability.health import HealthStatus

    # Test _build_snapshot with custom client mock
    from unittest.mock import MagicMock
    mock_client = MagicMock()
    mock_client.get_operations_snapshot.return_value = "dummy-snapshot"
    res = dash_module._build_snapshot(client=mock_client)
    assert res == "dummy-snapshot"

    # Test status color mapping
    assert dash_module._status_color(HealthStatus.HEALTHY) == "🟢"
    assert dash_module._status_color(HealthStatus.DEGRADED) == "🟡"
    assert dash_module._status_color(HealthStatus.UNHEALTHY) == "🔴"
    assert dash_module._status_color(HealthStatus.UNKNOWN) == "⚪"
    assert dash_module._status_color("other") == "⚪"

    # Test status badge mapping
    assert "HEALTHY" in dash_module._status_badge(HealthStatus.HEALTHY)
    assert "DEGRADED" in dash_module._status_badge(HealthStatus.DEGRADED)


def test_topic_collection_manual_topic_and_staged_prompt(tmp_path: Path) -> None:
    """Phase 2D: Verify 1_topic_collection.py renders custom topic form and dynamic prompt."""
    at = AppTest.from_file("src/content_creation/ui/pages/1_topic_collection.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0, f"Page crashed with: {at.exception}"

    # Verify custom topic form header is present
    headers = [m.value for m in at.markdown]
    assert any("Add Custom Topic / Idea" in h for h in headers)

    # When staged is empty, verify notice
    infos = [i.value for i in at.info]
    assert any("Run feed collection to download papers" in i for i in infos)


def test_asset_workshop_blocking_reasons_and_cue_blocks(tmp_path: Path) -> None:
    """UI-006 & Phase 2D: Verify blocking reasons are rendered as badges and not raw python list."""
    topic_id = "topic-test-cue-ui"
    (tmp_path / "data" / "briefs" / f"{topic_id}.json").write_text(
        json.dumps(_make_brief_dict(topic_id)), encoding="utf-8"
    )
    manifest_dict = _make_manifest_dict(topic_id)
    manifest_dict["blocking_reasons"] = ["script: missing", "carousel: review_rejected"]
    (tmp_path / "data" / "manifests" / f"{topic_id}.json").write_text(
        json.dumps(manifest_dict), encoding="utf-8"
    )

    at = AppTest.from_file("src/content_creation/ui/pages/5_asset_workshop.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0, f"Page crashed with: {at.exception}"

    all_markdown = " ".join(m.value for m in at.markdown)
    # Verify blocking reasons rendered as badges, NOT raw list repr "['script: missing'..."
    assert "['script: missing'" not in all_markdown
    assert "🚫 `script: missing`" in all_markdown
    assert "🚫 `carousel: review_rejected`" in all_markdown


def test_app_page_latex_escape_and_navigation(tmp_path: Path) -> None:
    """UI-003 & Phase 2D: Verify app.py renders clean arrow characters and stage navigation."""
    at = AppTest.from_file("src/content_creation/ui/app.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0, f"Page crashed with: {at.exception}"

    all_markdown = " ".join(m.value for m in at.markdown)
    # Verify LaTeX escape $\rightarrow$ is fixed to clean Unicode arrow →
    assert r"$\rightarrow$" not in all_markdown
    assert r"\rightarrow" not in all_markdown
    assert "Collect → Score → Briefs → CI → Storyboards → Assets → Manifests" in all_markdown

    # Verify app.py contains st.page_link calls for stage navigation
    app_source = Path("src/content_creation/ui/app.py").read_text(encoding="utf-8")
    assert "page_link" in app_source
    assert "pages/1_topic_collection.py" in app_source
    assert "pages/2_topic_pipeline.py" in app_source
    assert "pages/3_brief_viewer.py" in app_source
    assert "pages/4_storyboard.py" in app_source
    assert "pages/5_asset_workshop.py" in app_source


def test_topic_pipeline_read_only_expander_and_priority_tier_badges(tmp_path: Path) -> None:
    """UI-004 & Phase 2D: Verify 2_topic_pipeline.py uses read-only weights expander and tier badges."""
    # Seed scored topics in test workspace
    scored_dir = tmp_path / "data" / "scored"
    scored_dir.mkdir(parents=True, exist_ok=True)
    item_dict = {
        "id": "topic-tier-test-1",
        "title": "High Priority Research Paper",
        "url": "https://example.com/p1",
        "source": "arxiv",
        "published_at": "2026-11-22T00:00:00Z",
        "author": "Test Author",
        "raw_text": "Sample raw text content " * 10,
        "summary": "Summary",
        "category": "paper",
        "status": "scored",
        "validation_flags": [],
        "priority_score": 85.0,
        "novelty_score": 8.0,
        "student_usefulness_score": 9.0,
        "credibility_score": 8.5,
        "explainability_score": 8.0,
        "hook_potential_score": 8.0,
        "scoring_rules_fired": ["rule1"],
        "scored_at": "2026-11-22T00:00:00Z",
    }
    (scored_dir / "topic-tier-test-1.json").write_text(json.dumps(item_dict), encoding="utf-8")

    at = AppTest.from_file("src/content_creation/ui/pages/2_topic_pipeline.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0, f"Page crashed with: {at.exception}"

    # Verify expander label exists
    expanders = [e.label for e in at.expander]
    assert any("Current Scoring Weights (config/scoring.yaml)" in exp for exp in expanders)

    # Sliders should NOT exist on Page 2 anymore
    assert len(at.slider) == 0

    # Verify forward page_link to Page 3 exists in source
    p2_source = Path("src/content_creation/ui/pages/2_topic_pipeline.py").read_text(encoding="utf-8")
    assert 'page_link("pages/3_brief_viewer.py"' in p2_source


def test_brief_viewer_status_badge_and_no_duplicate_summary(tmp_path: Path) -> None:
    """UI-005 & Phase 2D: Verify 3_brief_viewer.py formats needs_review and removes duplicate summary."""
    topic_id = "topic-brief-ui-test"
    # Seed scored topic so selectbox populates
    scored_dir = tmp_path / "data" / "scored"
    scored_dir.mkdir(parents=True, exist_ok=True)
    item_dict = {
        "id": topic_id,
        "title": "Needs Review Paper",
        "url": "https://example.com/p2",
        "source": "arxiv",
        "published_at": "2026-11-22T00:00:00Z",
        "raw_text": "Sample research text " * 10,
        "category": "paper",
        "status": "scored",
        "priority_score": 75.0,
        "validation_flags": [],
    }
    (scored_dir / f"{topic_id}.json").write_text(json.dumps(item_dict), encoding="utf-8")

    brief_dict = _make_brief_dict(topic_id)
    brief_dict["review_status"] = "needs_review"
    (tmp_path / "data" / "briefs" / f"{topic_id}.json").write_text(
        json.dumps(brief_dict), encoding="utf-8"
    )

    at = AppTest.from_file("src/content_creation/ui/pages/3_brief_viewer.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0, f"Page crashed with: {at.exception}"

    all_markdown = " ".join(m.value for m in at.markdown)
    # Verify status is rendered as "Pending review ⏳" rather than raw "needs_review"
    assert "Pending review ⏳" in all_markdown

    # Verify duplicate "Brief Summary" header is removed
    assert "### 📄 Brief Summary" not in all_markdown

    # Verify forward page_link to Page 4 exists in source
    p3_source = Path("src/content_creation/ui/pages/3_brief_viewer.py").read_text(encoding="utf-8")
    assert 'page_link("pages/4_storyboard.py"' in p3_source


def test_storyboard_selector_readiness_indicator(tmp_path: Path) -> None:
    """Phase 2D: Verify 4_storyboard.py shows readiness emojis in selector."""
    topic_id = "topic-sb-ready-test"
    (tmp_path / "data" / "briefs" / f"{topic_id}.json").write_text(
        json.dumps(_make_brief_dict(topic_id)), encoding="utf-8"
    )
    (tmp_path / "data" / "storyboards" / f"{topic_id}.json").write_text(
        json.dumps(_make_storyboard_dict(topic_id)), encoding="utf-8"
    )

    at = AppTest.from_file("src/content_creation/ui/pages/4_storyboard.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0, f"Page crashed with: {at.exception}"

    # Verify Brief Selector has the ✅ icon indicating storyboard readiness
    brief_selector = next((sb for sb in at.selectbox if "Brief Selector" in sb.label), None)
    assert brief_selector is not None
    assert any("✅" in opt for opt in brief_selector.options)

    # Verify forward page_link to Page 5 exists in source
    p4_source = Path("src/content_creation/ui/pages/4_storyboard.py").read_text(encoding="utf-8")
    assert 'page_link("pages/5_asset_workshop.py"' in p4_source


def test_all_ui_files_ast_zero_direct_layer_violations() -> None:
    """Architectural Guardrail: Verify all UI files have 0 direct imports of DB or storage repos."""
    import ast

    ui_files = [
        Path("src/content_creation/ui/app.py"),
        Path("src/content_creation/ui/pages/1_topic_collection.py"),
        Path("src/content_creation/ui/pages/2_topic_pipeline.py"),
        Path("src/content_creation/ui/pages/3_brief_viewer.py"),
        Path("src/content_creation/ui/pages/4_storyboard.py"),
        Path("src/content_creation/ui/pages/5_asset_workshop.py"),
        Path("src/content_creation/ui/pages/6_operations_dashboard.py"),
    ]

    forbidden_prefixes = [
        "sqlite3",
        "content_creation.platform.storage.local",
        "content_creation.platform.storage.database",
        "content_creation.jobs",
        "content_creation.events.store",
        "content_creation.metrics",
        "content_creation.audit",
        "content_creation.inference.providers",
    ]

    for file_path in ui_files:
        assert file_path.exists(), f"Missing UI file: {file_path}"
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_prefixes:
                        assert not alias.name.startswith(forbidden), (
                            f"Prohibited import '{alias.name}' found in {file_path}"
                        )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for forbidden in forbidden_prefixes:
                    assert not mod.startswith(forbidden), (
                        f"Prohibited 'from {mod} import ...' found in {file_path}"
                    )


# ---------------------------------------------------------------------------
# Interactive Headless Streamlit AppTest Suite (Phase 2D QA)
# ---------------------------------------------------------------------------

def test_topic_collection_form_submission_success(tmp_path: Path) -> None:
    """Stage 1 UI: Test submitting custom topic form creates and persists staged item."""
    at = AppTest.from_file("src/content_creation/ui/pages/1_topic_collection.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0

    # Fill form fields
    at.text_input[0].input("DeepSeek-R1 Architecture")
    at.text_area[0].input("Incentivizing reasoning capability through reinforcement learning without supervised fine-tuning.")
    at.text_input[1].input("https://arxiv.org/abs/2501.12948")
    at.text_input[2].input("arxiv")

    # Submit form
    at.button[0].click().run()
    assert len(at.exception) == 0

    # Verify file written to data/staged
    staged_files = list((tmp_path / "data" / "staged").glob("*.json"))
    assert len(staged_files) >= 1
    staged_data = json.loads(staged_files[0].read_text(encoding="utf-8"))
    assert staged_data["title"] == "DeepSeek-R1 Architecture"
    assert staged_data["source"] == "arxiv"
    assert staged_data["status"] == "staged"


def test_topic_collection_form_submission_empty_title_validation(tmp_path: Path) -> None:
    """Stage 1 UI: Test submitting custom topic form with empty title triggers validation error."""
    at = AppTest.from_file("src/content_creation/ui/pages/1_topic_collection.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0

    at.text_input[0].input("   ")
    at.text_area[0].input("Some notes")
    at.button[0].click().run()

    assert len(at.exception) == 0
    errors = [e.value for e in at.error]
    assert any("Topic title is required" in err for err in errors)


def test_topic_collection_form_submission_empty_notes_validation(tmp_path: Path) -> None:
    """Stage 1 UI: Test submitting custom topic form with empty notes triggers validation error."""
    at = AppTest.from_file("src/content_creation/ui/pages/1_topic_collection.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0

    at.text_input[0].input("Valid Title")
    at.text_area[0].input("   ")
    at.button[0].click().run()

    assert len(at.exception) == 0
    errors = [e.value for e in at.error]
    assert any("Notes or research excerpt is required" in err for err in errors)


def test_topic_pipeline_interactive_filters_and_tier_badges(tmp_path: Path) -> None:
    """ERR-029: Verify Page 2 displays all three priority tier badges and read-only weights expander."""
    scored_dir = tmp_path / "data" / "scored"
    scored_dir.mkdir(parents=True, exist_ok=True)

    # Seed 3 scored topics across High (>=80), Medium (50-79), Low (<50)
    for idx, (score, label) in enumerate([(85.0, "High"), (65.0, "Med"), (35.0, "Low")], start=1):
        item_dict = {
            "id": f"topic-tier-{idx}",
            "title": f"Paper {label} {idx}",
            "url": f"https://example.com/p{idx}",
            "source": "arxiv",
            "published_at": "2026-11-22T00:00:00Z",
            "raw_text": "Sample text " * 10,
            "category": "paper",
            "status": "scored",
            "priority_score": score,
            "validation_flags": [],
        }
        (scored_dir / f"topic-tier-{idx}.json").write_text(json.dumps(item_dict), encoding="utf-8")

    at = AppTest.from_file("src/content_creation/ui/pages/2_topic_pipeline.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0

    # Verify all 3 priority tier badges render in the triage dataframe
    assert len(at.dataframe) >= 1
    df_val = at.dataframe[0].value
    if hasattr(df_val, "to_dict"):
        tiers = list(df_val["Priority Tier"])
    else:
        tiers = [row["Priority Tier"] for row in df_val]  # type: ignore[union-attr]

    assert "🟢 High" in tiers
    assert "🟡 Medium" in tiers
    assert "⚪ Low" in tiers

    # Sliders must be zero
    assert len(at.slider) == 0

    # Read-only scoring weights expander
    expanders = [e.label for e in at.expander]
    assert any("Current Scoring Weights (config/scoring.yaml)" in exp for exp in expanders)


def test_brief_viewer_interactive_status_badges(tmp_path: Path) -> None:
    """ERR-030: Verify 3_brief_viewer.py renders Pending review ⏳ and eliminates duplicate summary."""
    topic_id = "topic-brief-interactive"
    scored_dir = tmp_path / "data" / "scored"
    scored_dir.mkdir(parents=True, exist_ok=True)
    item_dict = {
        "id": topic_id,
        "title": "Interactive Brief Test Paper",
        "url": "https://example.com/p_interactive",
        "source": "arxiv",
        "published_at": "2026-11-22T00:00:00Z",
        "raw_text": "Sample text " * 10,
        "category": "paper",
        "status": "scored",
        "priority_score": 75.0,
        "validation_flags": [],
    }
    (scored_dir / f"{topic_id}.json").write_text(json.dumps(item_dict), encoding="utf-8")

    brief_dict = _make_brief_dict(topic_id)
    brief_dict["review_status"] = "needs_review"
    (tmp_path / "data" / "briefs" / f"{topic_id}.json").write_text(
        json.dumps(brief_dict), encoding="utf-8"
    )

    at = AppTest.from_file("src/content_creation/ui/pages/3_brief_viewer.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0

    all_markdown = " ".join(m.value for m in at.markdown)
    assert "Pending review ⏳" in all_markdown
    assert "### 📄 Brief Summary" not in all_markdown


def test_storyboard_page_interactive_selector_and_navigation(tmp_path: Path) -> None:
    """Stage 5 UI: Verify 4_storyboard.py options show readiness emojis and forward stage navigation."""
    topic_ready = "topic-ready-sb"
    topic_pending = "topic-pending-sb"

    (tmp_path / "data" / "briefs" / f"{topic_ready}.json").write_text(
        json.dumps(_make_brief_dict(topic_ready)), encoding="utf-8"
    )
    (tmp_path / "data" / "briefs" / f"{topic_pending}.json").write_text(
        json.dumps(_make_brief_dict(topic_pending)), encoding="utf-8"
    )

    # Storyboard exists only for topic_ready
    (tmp_path / "data" / "storyboards" / f"{topic_ready}.json").write_text(
        json.dumps(_make_storyboard_dict(topic_ready)), encoding="utf-8"
    )

    at = AppTest.from_file("src/content_creation/ui/pages/4_storyboard.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0

    # Brief selector contains ✅ for ready topic and ⏳ for pending topic
    brief_selector = next((sb for sb in at.selectbox if "Brief Selector" in sb.label), None)
    assert brief_selector is not None
    assert any("✅" in opt for opt in brief_selector.options)
    assert any("⏳" in opt for opt in brief_selector.options)


def test_asset_workshop_interactive_blocking_badges_and_cue_blocks(tmp_path: Path) -> None:
    """ERR-031: Verify 5_asset_workshop.py formats blocking reasons as badges and renders cue sheets."""
    topic_id = "topic-blocking-badges"
    (tmp_path / "data" / "briefs" / f"{topic_id}.json").write_text(
        json.dumps(_make_brief_dict(topic_id)), encoding="utf-8"
    )
    (tmp_path / "data" / "storyboards" / f"{topic_id}.json").write_text(
        json.dumps(_make_storyboard_dict(topic_id)), encoding="utf-8"
    )

    # Seed script
    scripts_dir = tmp_path / "data" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_dict = {
        "topic_id": topic_id,
        "format": "short_video",
        "hook": "Ever wondered how flash attention works?",
        "script_sections": ["Section 1", "Section 2"],
        "cta": "Check the repo link below.",
        "claims_used": ["Fast GPU compute"],
        "source_links": ["https://arxiv.org/abs/2407.08608"],
        "review_status": "draft",
        "generated_at": "2026-11-22T00:00:00Z",
    }
    (scripts_dir / f"{topic_id}.json").write_text(json.dumps(script_dict), encoding="utf-8")

    # Manifest with multiple blocking reasons
    manifest_dict = _make_manifest_dict(topic_id)
    manifest_dict["blocking_reasons"] = ["script: missing", "carousel: review_rejected", "newsletter: missing"]
    (tmp_path / "data" / "manifests" / f"{topic_id}.json").write_text(
        json.dumps(manifest_dict), encoding="utf-8"
    )

    at = AppTest.from_file("src/content_creation/ui/pages/5_asset_workshop.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0

    all_markdown = " ".join(m.value for m in at.markdown)
    # Raw Python list bracket representation must NOT appear
    assert "['script: missing'" not in all_markdown
    # Each blocking reason rendered as individual badge
    assert "🚫 `script: missing`" in all_markdown
    assert "🚫 `carousel: review_rejected`" in all_markdown
    assert "🚫 `newsletter: missing`" in all_markdown

    # Verify Production Cue Sheet and Voiceover code blocks appear
    all_codes = [c.value for c in at.code]
    assert any("PRODUCTION CUE SHEET" in code for code in all_codes)


def test_operations_dashboard_retired_sse_and_worker_offline_downgrade(tmp_path: Path) -> None:
    """ERR-032 & ERR-033: Verify Page 6 excludes SSE and downgrades worker offline alert to info."""
    at = AppTest.from_file("src/content_creation/ui/pages/6_operations_dashboard.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0

    all_markdown = " ".join(m.value for m in at.markdown)
    # ERR-032: Legacy SSE component must not be rendered
    assert "SSE Streaming: UNKNOWN" not in all_markdown
    assert "SSE" not in all_markdown

    # ERR-033: Worker offline alert in manual mode without jobs is not a yellow warning
    warnings = [w.value for w in at.warning]
    assert not any("Worker Daemon" in w for w in warnings)


def test_all_pages_ast_zero_deprecated_parameters_and_html_components() -> None:
    """ERR-022: Enforce zero use_container_width, zero st.components.v1.html, and clean unicode arrows."""
    import ast

    ui_files = [
        Path("src/content_creation/ui/app.py"),
        Path("src/content_creation/ui/pages/1_topic_collection.py"),
        Path("src/content_creation/ui/pages/2_topic_pipeline.py"),
        Path("src/content_creation/ui/pages/3_brief_viewer.py"),
        Path("src/content_creation/ui/pages/4_storyboard.py"),
        Path("src/content_creation/ui/pages/5_asset_workshop.py"),
        Path("src/content_creation/ui/pages/6_operations_dashboard.py"),
    ]

    for file_path in ui_files:
        assert file_path.exists(), f"File {file_path} missing"
        content = file_path.read_text(encoding="utf-8")

        # Zero LaTeX arrow escapes
        assert r"$\rightarrow$" not in content, f"LaTeX escape found in {file_path}"
        assert r"\rightarrow" not in content, f"LaTeX escape found in {file_path}"

        tree = ast.parse(content)
        for node in ast.walk(tree):
            # Zero use_container_width keyword arguments
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    assert kw.arg != "use_container_width", (
                        f"Deprecated keyword 'use_container_width' found at line {kw.lineno} in {file_path}"
                    )
            # Zero st.components.v1.html calls
            elif isinstance(node, ast.Attribute):
                if node.attr == "html" and isinstance(node.value, ast.Attribute) and node.value.attr == "v1":
                    assert False, f"Deprecated st.components.v1.html found at line {node.lineno} in {file_path}"



