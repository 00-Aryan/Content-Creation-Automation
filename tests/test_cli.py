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
            assert "usage:" in captured.out

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
