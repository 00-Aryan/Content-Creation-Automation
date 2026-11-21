"""Tests for CLI entry point."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from content_creation.cli import main


class TestCLI:
    """Test CLI behavior."""

    def test_cli_imports(self):
        """Test that CLI module can be imported without errors."""
        import content_creation.cli

        assert content_creation.cli is not None

    def test_version_flag(self, capsys):
        """Test --version flag."""
        with patch.object(sys, "argv", ["content-creation", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_help_flag(self, capsys):
        """Test --help flag."""
        with patch.object(sys, "argv", ["content-creation", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_status_command(self, capsys):
        """Test status command."""
        with patch.object(sys, "argv", ["content-creation", "status"]):
            result = main()
            assert result == 0
            captured = capsys.readouterr()
            assert "Status: Operational" in captured.out

    def test_collect_command_real(self, capsys):
        """Test collect command calls real ingestion logic."""
        with patch.object(sys, "argv", ["content-creation", "collect", "--source", "arxiv"]):
            with patch("content_creation.ingestion.IngestionEngine.run", return_value=[]):
                result = main()
                assert result == 0
                captured = capsys.readouterr()
                assert "Ingestion complete" in captured.out

    def test_collect_command_all(self, capsys):
        """Test collect command with --all flag."""
        with patch.object(sys, "argv", ["content-creation", "collect", "--all"]):
            with patch("content_creation.ingestion.IngestionEngine.run", return_value=[]):
                result = main()
                assert result == 0
                captured = capsys.readouterr()
                assert "Ingestion complete" in captured.out

    def test_no_command_shows_help(self, capsys):
        """Test that no command shows help."""
        with patch.object(sys, "argv", ["content-creation"]):
            result = main()
            assert result == 0
            captured = capsys.readouterr()
            assert "usage:" in captured.out.lower()

    def test_keyboard_interrupt(self):
        """Test KeyboardInterrupt handling."""
        with patch.object(sys, "argv", ["content-creation", "status"]):
            with patch("content_creation.cli.setup_logging", side_effect=KeyboardInterrupt):
                result = main()
                assert result == 130

    def test_exception_handler_uses_unshadowed_sys(self, capsys):
        """Test that main() error handler writes to sys.stderr without UnboundLocalError."""
        with patch.object(sys, "argv", ["content-creation", "status"]):
            with patch("content_creation.cli.LocalStorage", side_effect=RuntimeError("storage disk full")):
                result = main()
                assert result == 1
                captured = capsys.readouterr()
                assert "Error: storage disk full" in captured.err

    def test_plan_week_default_date_uses_unshadowed_timedelta(self):
        """Test plan-week computes default date using module-level timedelta."""
        mock_calendar = MagicMock(
            week_start="2026-11-23",
            week_end="2026-11-29",
            generated_at="2026-11-20T12:00:00",
            total_posts=0,
            format_counts={},
            topics_used=[],
            posts=[],
        )
        with patch.object(sys, "argv", ["content-creation", "plan-week"]):
            with patch("content_creation.workflow.WorkflowActionExecutor.execute") as mock_exec:
                mock_exec.return_value = MagicMock(success=True, raw_result=mock_calendar)
                with patch("content_creation.storage.local.LocalStorage.save_calendar", return_value="dummy.json"):
                    with patch("pathlib.Path.open", create=True):
                        result = main()
                        assert result == 0
                        assert mock_exec.called

    def test_plan_week_runtime_execution_isolated_dir(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-001: real runtime execution of plan-week calculates default Monday via timedelta."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        with patch.object(sys, "argv", ["content-creation", "plan-week"]):
            result = main()
            # Returns 1 due to no topics in clean staging, but executes timedelta math without UnboundLocalError
            assert result == 1
            captured = capsys.readouterr()
            assert "Error planning week:" in captured.out
            assert "UnboundLocalError" not in captured.err
            assert "UnboundLocalError" not in captured.out

    def test_plan_week_daily_schedule_loop_uses_timedelta(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-001: plan-week daily schedule loop executes day_offset timedelta calculation without UnboundLocalError."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "calendars").mkdir(parents=True, exist_ok=True)

        post1 = MagicMock(day=1, format="short_video", topic_title="Topic 1", asset_path="path/1")
        post2 = MagicMock(day=3, format="carousel", topic_title="Topic 2", asset_path="path/2")
        mock_calendar = MagicMock(
            week_start="2026-11-23",
            week_end="2026-11-29",
            generated_at="2026-11-20T12:00:00",
            total_posts=2,
            format_counts={"short_video": 1, "carousel": 1},
            topics_used=["t1", "t2"],
            posts=[post1, post2],
        )

        with patch.object(sys, "argv", ["content-creation", "plan-week", "--week-start", "2026-11-23"]):
            with patch("content_creation.workflow.WorkflowActionExecutor.execute") as mock_exec:
                mock_exec.return_value = MagicMock(success=True, raw_result=mock_calendar)
                with patch("content_creation.storage.local.LocalStorage.save_calendar", return_value=str(tmp_path / "data" / "calendars" / "2026-11-23.json")):
                    result = main()
                    assert result == 0
                    captured = capsys.readouterr()
                    assert "Week planned: 2026-11-23 to 2026-11-29" in captured.out
                    md_path = tmp_path / "data" / "calendars" / "2026-11-23.md"
                    assert md_path.exists()
                    content = md_path.read_text(encoding="utf-8")
                    assert "Day 1 — 2026-11-23 (Monday)" in content
                    assert "Day 3 — 2026-11-25 (Wednesday)" in content

    def test_dry_run_runtime_execution_isolated_dir(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-001: real runtime execution of dry-run calculates default Monday via timedelta."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        with patch.object(sys, "argv", ["content-creation", "dry-run"]):
            result = main()
            # Returns 1 due to no topics in clean staging, but executes timedelta math without UnboundLocalError
            assert result == 1
            captured = capsys.readouterr()
            assert "Error planning week for dry-run:" in captured.out
            assert "UnboundLocalError" not in captured.err
            assert "UnboundLocalError" not in captured.out

    def test_init_analytics_runtime_execution_isolated_dir(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-001: real runtime execution of init-analytics calculates default Monday via timedelta."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        with patch.object(sys, "argv", ["content-creation", "init-analytics"]):
            result = main()
            # Returns 1 due to missing calendar in clean staging, but executes timedelta math without UnboundLocalError
            assert result == 1
            captured = capsys.readouterr()
            assert "Error executing init-analytics:" in captured.out
            assert "UnboundLocalError" not in captured.err
            assert "UnboundLocalError" not in captured.out

    def test_metrics_summary_empty_store_isolated_dir(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-001: metrics-summary returns 0 cleanly when no metrics store found."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        with patch.object(sys, "argv", ["content-creation", "metrics-summary"]):
            result = main()
            assert result == 0
            captured = capsys.readouterr()
            assert "No metrics store found." in captured.out

    def test_metrics_summary_runtime_execution_with_telemetry_data(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-001: metrics-summary executes timedelta date math and accesses unshadowed sys_summary."""
        monkeypatch.chdir(tmp_path)
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        from content_creation.metrics import SQLiteMetricRepository
        from content_creation.events.store import SQLiteEventRepository

        m_repo = SQLiteMetricRepository(str(data_dir / "metrics.db"))
        m_repo.close()
        e_repo = SQLiteEventRepository(str(data_dir / "events.db"))
        e_repo.close()

        with patch.object(sys, "argv", ["content-creation", "metrics-summary", "--days", "7"]):
            result = main()
            assert result == 0
            captured = capsys.readouterr()
            assert "Telemetry Summary (last 7 days)" in captured.out
            assert "System:" in captured.out
            assert "Events stored:" in captured.out
            assert "Metrics stored:" in captured.out

    def test_metrics_kpi_runtime_execution(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-001: metrics-kpi executes timedelta date math for report window without UnboundLocalError."""
        monkeypatch.chdir(tmp_path)
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        from content_creation.metrics import SQLiteMetricRepository

        m_repo = SQLiteMetricRepository(str(data_dir / "metrics.db"))
        m_repo.close()

        with patch.object(sys, "argv", ["content-creation", "metrics-kpi", "--days", "14"]):
            result = main()
            assert result == 0
            captured = capsys.readouterr()
            assert "KPI Report (last 14 days)" in captured.out
            assert "Workflow KPIs:" in captured.out

    def test_main_exception_handler_verbose_mode(self, capsys):
        """Covers ERR-001: main() exception handler writes to sys.stderr and prints traceback when verbose."""
        with patch.object(sys, "argv", ["content-creation", "-v", "status"]):
            with patch("content_creation.cli.LocalStorage", side_effect=ValueError("corrupt storage configuration")):
                result = main()
                assert result == 1
                captured = capsys.readouterr()
                assert "Error: corrupt storage configuration" in captured.err
                assert "Traceback (most recent call last):" in captured.err

    def test_generate_ci_and_storyboards_commands(self, capsys):
        """Covers ERR-009: verify generate-ci and generate-storyboards dispatch via WorkflowActionExecutor."""
        mock_res = MagicMock(success=True, affected_artifacts={"generated_count": "3", "failures": "0"})
        with patch("content_creation.workflow.WorkflowActionExecutor.execute", return_value=mock_res):
            with patch.object(sys, "argv", ["content-creation", "generate-ci", "--top", "3"]):
                assert main() == 0
                captured = capsys.readouterr()
                assert "Generated 3 content intelligence items" in captured.out

            with patch.object(sys, "argv", ["content-creation", "generate-storyboards", "--top", "3"]):
                assert main() == 0
                captured = capsys.readouterr()
                assert "Generated 3 storyboards" in captured.out
