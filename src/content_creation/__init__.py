"""Content Creation Factory - A source-grounded content pipeline for ML/AI students."""

__version__ = "0.1.0"
__author__ = "Aryan"

from content_creation.utils.logging import setup_logging
from content_creation.utils.config import get_config

__all__ = ["__version__", "setup_logging", "get_config"]
