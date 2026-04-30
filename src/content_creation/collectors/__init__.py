"""Collectors for fetching topics from various sources."""

from .base import BaseCollector
from .rss import RSSCollector

__all__ = ["BaseCollector", "RSSCollector"]
