"""Logging configuration and utilities."""

import json
import logging
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from content_creation.security.redaction import redact_mapping, redact_text


class RedactingFormatter(logging.Formatter):
    """Logging Formatter that redacts secrets from format results."""

    def format(self, record: logging.LogRecord) -> str:
        orig_msg = record.msg
        orig_args = record.args

        # Redact the message if it's a string
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)

        # Redact arguments if they are strings
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_text(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_text(str(v)) if isinstance(v, str) else v
                    for v in record.args
                )

        try:
            formatted = super().format(record)
        finally:
            record.msg = orig_msg
            record.args = orig_args

        return formatted


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Configure logging for the application.

    Args:
        level: Logging level (default: INFO).
        log_file: Optional path to a log file. If None, logs to stdout only.
        format_string: Custom format string. If None, uses default.

    Returns:
        The root logger configured with the specified settings.
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    formatter = RedactingFormatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        A logger instance.
    """
    return logging.getLogger(name)


class PipelineLogger:
    """Structured JSON-line logger for pipeline runs."""

    def __init__(self, log_path: Path):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path = log_path
        self.entries: list = []

    def log(self, stage: str, event: str, details: Optional[Dict[str, Any]] = None, duration_s: Optional[float] = None):
        redacted_details = redact_mapping(details) if details else {}
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "event": event,
            "duration_s": duration_s,
            "details": redacted_details,
        }
        self.entries.append(entry)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    @contextmanager
    def stage(self, stage_name: str):
        """Context manager that auto-logs start/end/duration and catches errors."""
        self.log(stage_name, "start")
        start = time.time()
        result: Dict[str, Any] = {"status": "success", "error": None}
        try:
            yield result
        except Exception as e:
            result["status"] = "error"
            result["error"] = redact_text(str(e))
            raise
        finally:
            duration = time.time() - start
            self.log(stage_name, "end", details=result, duration_s=round(duration, 2))

    def summary(self) -> Dict[str, Dict[str, Any]]:
        """Return stage summaries for printing."""
        stages: Dict[str, Dict[str, Any]] = {}
        for entry in self.entries:
            if entry["event"] == "end":
                stages[entry["stage"]] = {
                    "status": entry["details"].get("status", "unknown"),
                    "duration_s": entry["duration_s"],
                    "details": entry["details"],
                }
        return stages
