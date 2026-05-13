"""Tests for CLI entry point."""

import sys
from unittest.mock import patch

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
