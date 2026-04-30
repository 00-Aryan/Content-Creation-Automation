"""RSS/Atom feed collector."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import feedparser
from content_creation.collectors.base import BaseCollector
from content_creation.models.topic import TopicCategory, TopicItem, TopicStatus


class RSSCollector(BaseCollector):
    """Collector for RSS and Atom feeds."""

    def fetch(self) -> Any:
        """Fetch the feed using feedparser."""
        url = self.config.get("url")
        if not url:
            raise ValueError(f"No URL configured for source {self.source_id}")
        
        return feedparser.parse(url)

    def parse(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Extract entries from the parsed feed."""
        return raw_data.entries

    def normalize(self, record: Dict[str, Any]) -> TopicItem:
        """Normalize an RSS entry into a TopicItem."""
        url = record.get("link", "")
        if not url:
            # Fallback to id if link is missing, though rare for RSS
            url = record.get("id", "")
        
        title = record.get("title", "Untitled")
        
        # Parse publication date
        published_at = "unknown"
        for date_key in ["published_parsed", "updated_parsed", "created_parsed"]:
            date_struct = record.get(date_key)
            if date_struct:
                published_at = datetime(*date_struct[:6]).isoformat()
                break
        
        # Handle author
        author = record.get("author")
        if not author and "authors" in record and record.authors:
            author = record.authors[0].get("name")
        
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
            category = TopicCategory.UNKNOWN
            
        tags = [tag.get("term") for tag in record.get("tags", []) if tag.get("term")]

        return TopicItem(
            id=TopicItem.generate_id(url),
            title=title,
            url=url,
            source=self.source_name or "unknown",
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
