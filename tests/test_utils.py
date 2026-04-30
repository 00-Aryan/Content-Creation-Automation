"""Tests for utility functions."""

import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from content_creation.utils.config import ConfigError, get_env_var, load_env_file
from content_creation.utils.logging import get_logger, setup_logging


class TestLogging:
    """Test logging utilities."""

    def test_setup_logging_default(self):
        """Test setup_logging with default parameters."""
        logger = setup_logging()
        assert logger is not None
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1

    def test_setup_logging_debug_level(self):
        """Test setup_logging with DEBUG level."""
        logger = setup_logging(level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_setup_logging_with_file(self, tmp_path):
        """Test setup_logging with file output."""
        log_file = tmp_path / "test.log"
        logger = setup_logging(log_file=log_file)
        assert logger is not None
        assert log_file.exists()

    def test_setup_logging_custom_format(self):
        """Test setup_logging with custom format string."""
        custom_format = "%(levelname)s - %(message)s"
        logger = setup_logging(format_string=custom_format)
        assert logger is not None

    def test_get_logger(self):
        """Test get_logger returns a logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_same_name(self):
        """Test that get_logger returns same instance for same name."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        assert logger1 is logger2


class TestConfig:
    """Test configuration utilities."""

    def test_get_env_var_with_default(self):
        """Test get_env_var returns default when variable not set."""
        result = get_env_var("NONEXISTENT_VAR", default="default_value")
        assert result == "default_value"

    def test_get_env_var_required_missing(self):
        """Test get_env_var raises error when required variable is missing."""
        with pytest.raises(ConfigError) as exc_info:
            get_env_var("NONEXISTENT_VAR", required=True)
        assert "Required environment variable not set" in str(exc_info.value)

    def test_get_env_var_with_value(self):
        """Test get_env_var returns value when variable is set."""
        with patch.dict("os.environ", {"TEST_VAR": "test_value"}):
            result = get_env_var("TEST_VAR")
            assert result == "test_value"

    def test_get_env_var_default_override(self):
        """Test that set value overrides default."""
        with patch.dict("os.environ", {"TEST_VAR": "set_value"}):
            result = get_env_var("TEST_VAR", default="default_value")
            assert result == "set_value"

    def test_load_env_file_nonexistent(self):
        """Test load_env_file with nonexistent file (should not raise)."""
        # Should not raise an error
        load_env_file(Path("/nonexistent/.env"))

    def test_load_env_file_existing(self, tmp_path):
        """Test load_env_file with existing file."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=env_value\n")
        load_env_file(env_file)
        # Variable should be loaded into environment
        import os
        assert os.getenv("TEST_VAR") == "env_value"
