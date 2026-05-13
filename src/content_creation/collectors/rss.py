"""RSS/Atom feed collector."""

import logging

from datetime import datetime
from typing import Any, Dict, List, Optional

import feedparser
from content_creation.collectors.base import BaseCollector
from content_creation.models.topic import TopicCategory, TopicItem, TopicStatus

logger = logging.getLogger(__name__)


class RSSCollector(BaseCollector):
    """Collector for RSS and Atom feeds."""

    def fetch(self) -> Any:
        """Fetch the feed using feedparser."""
        url = self.config.get("url")
        if not url:
            raise ValueError(f"No URL configured for source {self.source_id}")
        
        result = feedparser.parse(url)
        
        # Log bozo as warning but proceed if entries are present
        if result.bozo:
            logger.warning(
                f"Feed at {url} is malformed (bozo flag): {result.bozo_exception}. "
                "Attempting to proceed with extracted entries."
            )
            if not result.entries:
                raise ValueError(f"Feed parse failed with bozo error and no entries: {result.bozo_exception}")
            
        # Raise on HTTP errors
        status = result.get("status", 200)
        if status >= 400:
            raise ValueError(f"HTTP error {status} fetching {url}")
            
        return result

    def parse(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Extract entries from the parsed feed."""
        return raw_data.entries

    def normalize(self, record: Dict[str, Any]) -> TopicItem:
        """Normalize an RSS entry into a TopicItem."""
        url = record.get("link", "")
        if not url:
            # Fallback to id if link is missing
            url = record.get("id", "")
            
        if not url:
            raise ValueError(f"Record has no link or id: {record}")
        
        title = record.get("title", "Untitled")
        
        # Parse publication date
        published_at = "unknown"
        for date_key in ["published_parsed", "updated_parsed", "created_parsed"]:
            date_struct = record.get(date_key)
            if date_struct and len(date_struct) >= 6:
                published_at = datetime(*date_struct[:6]).isoformat()
                break
        
        # Handle author defensively
        author = record.get("author")
        authors = record.get("authors")
        if not author and isinstance(authors, list) and authors:
            first_author = authors[0]
            if isinstance(first_author, dict):
                author = first_author.get("name")
            else:
                author = str(first_author)
        
        # Extract content/summary
        raw_text = record.get("content", [{"value": ""}])[0].get("value", "")
        if not raw_text:
            raw_text = record.get("summary", "")
        
        excerpt = record.get("summary", "")
        
        # Determine category from config or tags
        category_str = self.config.get("category", "unknown")
        try:
            category = TopicCategory(category_str)
        except ValueError:
            logger.warning(f"Invalid category '{category_str}' in config for {self.source_id}, using UNKNOWN")
            category = TopicCategory.UNKNOWN
            
        tags = [tag.get("term") for tag in record.get("tags", []) if tag.get("term")]

        return TopicItem(
            id=TopicItem.generate_id(url),
            title=title,
            url=url,
            source=self.source_name,
            published_at=published_at,
            author=author,
            raw_text=raw_text,
            excerpt=excerpt,
            category=category,
            topic_tags=tags,
            status=TopicStatus.RAW,
            metadata={
                "source_type": "rss",
                "feed_id": self.source_id
            }
        )
