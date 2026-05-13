"""Orchestration for the ingestion pipeline."""

import logging
from typing import Dict, Any, List, Optional

from content_creation.collectors.rss import RSSCollector
from content_creation.models.topic import TopicItem
from content_creation.storage.local import LocalStorage

logger = logging.getLogger(__name__)


class IngestionEngine:
    """Orchestrates the full ingestion pipeline."""

    def __init__(self, config: Dict[str, Any], storage: LocalStorage):
        """Initialize with configuration and storage.
        
        Args:
            config: Full application configuration dictionary.
            storage: LocalStorage instance for persistence.
        """
        self.config = config
        self.storage = storage

    def get_collectors(self, source_filter: Optional[str] = None):
        """Initialize collectors based on configuration."""
        collectors = []
        feeds = self.config.get("feeds", [])
        
        for feed_config in feeds:
            if not feed_config.get("enabled", True):
                continue
                
            if source_filter and feed_config.get("source") != source_filter and feed_config.get("id") != source_filter:
                continue
                
            # For Week 1, we only have RSSCollector
            collectors.append(RSSCollector(feed_config))
            
        return collectors

    def run(self, source_filter: Optional[str] = None) -> List[TopicItem]:
        """Run the ingestion pipeline."""
        collectors = self.get_collectors(source_filter)
        all_new_items = []
        
        for collector in collectors:
            logger.info(f"Starting collection for source: {collector.source_id}")
            try:
                # Fetch raw data for audit trail
                raw_data = collector.fetch()
                self.storage.save_raw(collector.source_id, raw_data)
                
                # Parse and normalize
                records = collector.parse(raw_data)
                logger.info(f"Fetched {len(records)} records from {collector.source_id}")
                
                new_count = 0
                duplicate_count = 0
                
                for record in records:
                    item = collector.normalize(record)
                    
                    # Deduplication
                    if self.storage.exists(item.id):
                        duplicate_count += 1
                        continue
                    
                    # Save staged item
                    try:
                        self.storage.save_staged(item)
                        all_new_items.append(item)
                        new_count += 1
                    except FileExistsError:
                        logger.debug(f"Item {item.id} was saved by another process, skipping.")
                        duplicate_count += 1
                        continue
                
                logger.info(f"Completed {collector.source_id}: {new_count} new, {duplicate_count} duplicates.")
                
            except Exception as e:
                logger.error(f"Failed collection for {collector.source_id}: {e}", exc_info=True)
                
        return all_new_items
