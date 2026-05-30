"""Shared type aliases used across all content domains.

These establish vocabulary ownership without introducing runtime behavior.
Future phases may evolve these types; this phase establishes ownership only.
"""

# TopicId is produced by TopicItem.generate_id(url) in models/topic.py.
# It is a SHA-256 hex digest of the source URL.
# All downstream models propagate this value without transformation.
TopicId = str
