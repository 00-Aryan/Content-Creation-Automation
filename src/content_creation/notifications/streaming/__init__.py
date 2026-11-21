"""Real-time notification streaming via Server-Sent Events (SSE).

Pure infrastructure layer. Deprecated per ADR-001 in favor of native
Streamlit fragments (@st.fragment) and ServiceClient facade.
"""

from content_creation.notifications.streaming.models import (
    StreamEventType,
    NotificationStreamEvent,
)
from content_creation.notifications.streaming.connection_manager import ConnectionManager
from content_creation.notifications.streaming.publisher import NotificationPublisher
from content_creation.notifications.streaming.server import NotificationSSEServer

__all__ = [
    "StreamEventType",
    "NotificationStreamEvent",
    "ConnectionManager",
    "NotificationPublisher",
    "NotificationSSEServer",
]
