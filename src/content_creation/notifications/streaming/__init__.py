"""Real-time notification streaming via Server-Sent Events (SSE).

Pure infrastructure layer. Deprecated per ADR-001 in favor of native
Streamlit fragments (@st.fragment) and ServiceClient facade.
Active streaming daemon, publisher, and connection manager components
have been retired.
"""

from content_creation.notifications.streaming.models import (
    StreamEventType,
    NotificationStreamEvent,
)

__all__ = [
    "StreamEventType",
    "NotificationStreamEvent",
]
