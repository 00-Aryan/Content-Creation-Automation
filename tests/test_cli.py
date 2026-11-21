"""Tests for CLI entry point."""

import sys
from datetime import date
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

    # ---------------------------------------------------------------------------
    # ERR-009: CLI Subcommand Parity & Missing Subcommands (generate-ci, generate-storyboards)
    # ---------------------------------------------------------------------------

    def test_generate_ci_custom_top_and_topic_id(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-009: generate-ci accepts --top and --topic-id options and dispatches to executor."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("GEMINI_API_KEY", "test-dummy-key")
        mock_res = MagicMock(success=True, affected_artifacts={"generated_count": "1", "failures": "0"})
        with patch("content_creation.workflow.WorkflowActionExecutor.execute", return_value=mock_res) as mock_exec:
            result = main(["generate-ci", "--top", "10", "--topic-id", "topic-ml-123"])
            assert result == 0
            assert mock_exec.called
            args, _ = mock_exec.call_args
            assert args[1] == "generate_ci"
            assert args[2] == "content_intelligence"
            assert args[3] == "topic-ml-123"
            assert args[4]["top_n"] == 10
            assert args[4]["api_key"] == "test-dummy-key"
            captured = capsys.readouterr()
            assert "Generated 1 content intelligence items, 0 failed" in captured.out

    def test_generate_ci_default_targets_all_with_default_top(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-009: generate-ci defaults to top 5 and target_id 'all' when --topic-id is omitted."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        mock_res = MagicMock(success=True, affected_artifacts={"generated_count": "5", "failures": "0"})
        with patch("content_creation.workflow.WorkflowActionExecutor.execute", return_value=mock_res) as mock_exec:
            result = main(["generate-ci"])
            assert result == 0
            args, _ = mock_exec.call_args
            assert args[3] == "all"
            assert args[4]["top_n"] == 5

    def test_generate_ci_unrecognized_all_option_returns_usage_error(self, capsys):
        """Covers ERR-009: generate-ci rejects unrecognized --all flag with exit code 2."""
        result = main(["generate-ci", "--all"])
        assert result == 2
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "No such option: --all" in combined

    def test_generate_ci_executor_failure_returns_exit_code_1(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-009: generate-ci returns exit code 1 and prints blocking reasons on execution failure."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        mock_res = MagicMock(success=False, blocking_reasons=["Brief for topic-ml-456 not approved"])
        with patch("content_creation.workflow.WorkflowActionExecutor.execute", return_value=mock_res):
            result = main(["generate-ci", "--topic-id", "topic-ml-456"])
            assert result == 1
            captured = capsys.readouterr()
            assert "Error during content intelligence generation: ['Brief for topic-ml-456 not approved']" in captured.out

    def test_generate_ci_missing_gemini_api_key_passes_none(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-009: generate-ci handles missing GEMINI_API_KEY gracefully without crashing."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        mock_res = MagicMock(success=True, affected_artifacts={"generated_count": "0", "failures": "0"})
        with patch("content_creation.workflow.WorkflowActionExecutor.execute", return_value=mock_res) as mock_exec:
            result = main(["generate-ci"])
            assert result == 0
            args, _ = mock_exec.call_args
            assert args[4]["api_key"] is None

    def test_generate_storyboards_custom_top_and_topic_id(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-009: generate-storyboards accepts --top and --topic-id options and dispatches to executor."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("GEMINI_API_KEY", "test-dummy-key")
        mock_res = MagicMock(success=True, affected_artifacts={"generated_count": "2", "failures": "1"})
        with patch("content_creation.workflow.WorkflowActionExecutor.execute", return_value=mock_res) as mock_exec:
            result = main(["generate-storyboards", "--top", "7", "--topic-id", "topic-sb-789"])
            assert result == 0
            assert mock_exec.called
            args, _ = mock_exec.call_args
            assert args[1] == "generate_storyboards"
            assert args[2] == "storyboard"
            assert args[3] == "topic-sb-789"
            assert args[4]["top_n"] == 7
            assert args[4]["api_key"] == "test-dummy-key"
            captured = capsys.readouterr()
            assert "Generated 2 storyboards, 1 failed" in captured.out

    def test_generate_storyboards_default_targets_all_with_default_top(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-009: generate-storyboards defaults to top 5 and target_id 'all' when --topic-id is omitted."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        mock_res = MagicMock(success=True, affected_artifacts={"generated_count": "5", "failures": "0"})
        with patch("content_creation.workflow.WorkflowActionExecutor.execute", return_value=mock_res) as mock_exec:
            result = main(["generate-storyboards"])
            assert result == 0
            args, _ = mock_exec.call_args
            assert args[3] == "all"
            assert args[4]["top_n"] == 5

    def test_generate_storyboards_unrecognized_all_option_returns_usage_error(self, capsys):
        """Covers ERR-009: generate-storyboards rejects unrecognized --all flag with exit code 2."""
        result = main(["generate-storyboards", "--all"])
        assert result == 2
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "No such option: --all" in combined

    def test_generate_storyboards_executor_failure_returns_exit_code_1(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-009: generate-storyboards returns exit code 1 and prints blocking reasons on failure."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        mock_res = MagicMock(success=False, blocking_reasons=["Content intelligence missing for topic-sb-001"])
        with patch("content_creation.workflow.WorkflowActionExecutor.execute", return_value=mock_res):
            result = main(["generate-storyboards", "--topic-id", "topic-sb-001"])
            assert result == 1
            captured = capsys.readouterr()
            assert "Error during storyboard generation: ['Content intelligence missing for topic-sb-001']" in captured.out

    def test_generate_storyboards_missing_gemini_api_key_passes_none(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-009: generate-storyboards handles missing GEMINI_API_KEY gracefully without crashing."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        mock_res = MagicMock(success=True, affected_artifacts={"generated_count": "0", "failures": "0"})
        with patch("content_creation.workflow.WorkflowActionExecutor.execute", return_value=mock_res) as mock_exec:
            result = main(["generate-storyboards"])
            assert result == 0
            args, _ = mock_exec.call_args
            assert args[4]["api_key"] is None

    # ---------------------------------------------------------------------------
    # ERR-012: Programmatic main() Contract, UTF-8 Exports, and Subcommand Dispatch
    # ---------------------------------------------------------------------------

    def test_main_programmatic_sequence_argument(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-012: main() accepts explicit argv sequence without depending on sys.argv."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        result = main(["status"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Status: Operational" in captured.out

    def test_main_programmatic_invalid_command_returns_code_2(self, capsys):
        """Covers ERR-012: main() returns exit code 2 on unknown subcommand."""
        result = main(["nonexistent-command-xyz"])
        assert result == 2
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "No such command" in combined or "error:" in combined.lower()

    def test_main_programmatic_invalid_option_returns_code_2(self, capsys):
        """Covers ERR-012: main() returns exit code 2 on invalid option flag."""
        result = main(["status", "--invalid-flag-12345"])
        assert result == 2
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "No such option" in combined or "error:" in combined.lower()

    def test_main_unhandled_exception_returns_code_1(self, capsys):
        """Covers ERR-012: main() catches unhandled exceptions, writes error to stderr, and returns exit code 1."""
        with patch("content_creation.cli.topics.get_context", side_effect=RuntimeError("unexpected database crash")):
            result = main(["status"])
            assert result == 1
            captured = capsys.readouterr()
            assert "Error: unexpected database crash" in captured.err

    def test_main_click_exception_with_exit_code_and_show_method(self, capsys):
        """Covers ERR-012: main() delegates to Click exception show() method and returns its exit_code."""
        import click
        exc = click.UsageError("custom usage issue")
        with patch("content_creation.cli.app", side_effect=exc):
            result = main(["status"])
            assert result == exc.exit_code
            captured = capsys.readouterr()
            assert "Error: custom usage issue" in (captured.out + captured.err)

    def test_main_click_exception_without_callable_show(self, capsys):
        """Covers ERR-012: main() handles Click exception without callable show method gracefully."""
        class MockClickException(Exception):
            exit_code = 4

        with patch("content_creation.cli.app", side_effect=MockClickException("custom exit issue")):
            result = main(["status"])
            assert result == 4
            captured = capsys.readouterr()
            assert "Error: custom exit issue" in captured.err

    def test_write_text_utf8_unicode_content(self, tmp_path):
        """Covers ERR-012: write_text_utf8 cleanly writes Unicode em-dashes, smart quotes, accented characters, and CJK."""
        from content_creation.cli.common import write_text_utf8

        test_file = tmp_path / "deep" / "nested" / "calendar_test.md"
        unicode_text = (
            "# Week 48 \u2014 Advanced AI Pipelines\n\n"
            "Quotes: \u201cState of the Art\u201d and \u2018Next-Gen\u2019\n"
            "Accents: caf\u00e9, r\u00e9sum\u00e9, \u00fcber\n"
            "Symbols: \u2014 \u2013 \u2192 \u2211 \u2208\n"
            "CJK & Emoji: \u667a\u80fd\u4f53 \U0001f680\n"
        )
        write_text_utf8(test_file, unicode_text)

        assert test_file.exists()
        raw_bytes = test_file.read_bytes()
        # Verify no CP1252 corruption: em-dash in UTF-8 is \xe2\x80\x94
        assert b"\xe2\x80\x94" in raw_bytes
        # Read back as UTF-8
        read_text = test_file.read_text(encoding="utf-8")
        assert read_text == unicode_text

    def test_plan_week_markdown_export_utf8_with_unicode_characters(self, tmp_path, monkeypatch, capsys):
        """Covers ERR-012: plan-week writes calendar markdown containing em-dashes and smart quotes using clean UTF-8."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "calendars").mkdir(parents=True, exist_ok=True)

        post1 = MagicMock(
            day=1,
            format="short_video",
            topic_title="Attention Is All You Need \u2014 \u201cTransformer Architecture\u201d",
            asset_path="path/1",
        )
        mock_calendar = MagicMock(
            week_start="2026-11-23",
            week_end="2026-11-29",
            generated_at="2026-11-20T12:00:00",
            total_posts=1,
            format_counts={"short_video": 1},
            topics_used=["t1"],
            posts=[post1],
        )

        with patch.object(sys, "argv", ["content-creation", "plan-week", "--week-start", "2026-11-23"]):
            with patch("content_creation.workflow.WorkflowActionExecutor.execute") as mock_exec:
                mock_exec.return_value = MagicMock(success=True, raw_result=mock_calendar)
                with patch(
                    "content_creation.storage.local.LocalStorage.save_calendar",
                    return_value=str(tmp_path / "data" / "calendars" / "2026-11-23.json"),
                ):
                    result = main()
                    assert result == 0
                    md_path = tmp_path / "data" / "calendars" / "2026-11-23.md"
                    assert md_path.exists()
                    content = md_path.read_text(encoding="utf-8")
                    assert "Attention Is All You Need \u2014 \u201cTransformer Architecture\u201d" in content
                    assert "\u2014" in content

    @pytest.mark.parametrize(
        "start_date,expected_monday",
        [
            (date(2026, 11, 23), date(2026, 11, 30)),  # Monday -> next Monday (7 days)
            (date(2026, 11, 24), date(2026, 11, 30)),  # Tuesday -> next Monday (6 days)
            (date(2026, 11, 25), date(2026, 11, 30)),  # Wednesday -> next Monday (5 days)
            (date(2026, 11, 28), date(2026, 11, 30)),  # Saturday -> next Monday (2 days)
            (date(2026, 11, 29), date(2026, 11, 30)),  # Sunday -> next Monday (1 day)
            (date(2026, 11, 30), date(2026, 12, 7)),   # Month rollover
            (date(2026, 12, 28), date(2027, 1, 4)),    # Year rollover
            (date(2028, 2, 28), date(2028, 3, 6)),     # Leap year Monday -> next Monday
            (date(2028, 2, 27), date(2028, 2, 28)),    # Leap year Sunday Feb 27 -> Monday Feb 28
        ],
    )
    def test_get_next_monday_bva_and_date_boundaries(self, start_date, expected_monday):
        """Covers ERR-012: verifies get_next_monday boundary value calculations across months, years, and leap years."""
        from content_creation.cli.common import get_next_monday

        assert get_next_monday(start_date) == expected_monday

    def test_get_next_monday_default_today(self):
        """Covers ERR-012: get_next_monday defaults to datetime.now(timezone.utc).date() when start_date is None."""
        from datetime import datetime, timezone
        from content_creation.cli.common import get_next_monday

        now_utc = datetime.now(timezone.utc).date()
        computed = get_next_monday()
        assert computed.weekday() == 0  # Must always be a Monday
        assert computed > now_utc
        assert (computed - now_utc).days <= 7

    @pytest.mark.parametrize(
        "subcommand",
        [
            # Topics
            "status",
            "list-topics",
            "validate-items",
            "review-scores",
            "scoring-dashboard",
            # Pipeline
            "collect",
            "score-topics",
            "generate-briefs",
            "generate-ci",
            "generate-storyboards",
            "generate-assets",
            "run-pipeline",
            # Planning
            "review-assets",
            "batch-approve",
            "build-manifest",
            "build-all-manifests",
            "plan-week",
            "dry-run",
            "init-analytics",
            "update-analytics",
            # Observability
            "event-timeline",
            "event-stats",
            "event-store",
            "event-tail",
            "event-replay",
            "event-cleanup",
            "metrics-kpi",
            "metrics-summary",
            "metrics-query",
            "metrics-cleanup",
            "metrics-rebuild",
            "audit-query",
            "audit-entity",
            "audit-actor",
            "audit-report",
            "audit-rebuild",
        ],
    )
    def test_subcommand_dispatch_and_help_text_rendering(self, subcommand, capsys):
        """Covers ERR-012: verifies all 34 domain subcommands render help text cleanly and return exit code 0."""
        result = main([subcommand, "--help"])
        assert result == 0
        captured = capsys.readouterr()
        assert f"{subcommand}" in captured.out

