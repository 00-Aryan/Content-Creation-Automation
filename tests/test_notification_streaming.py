"""Tests for SSE Streaming deprecation retiral and retained event models.

Verifies that deprecated socket-based SSE streaming components (ConnectionManager,
NotificationPublisher, NotificationSSEServer) are cleanly retired per ADR-001,
while domain models (StreamEventType, NotificationStreamEvent) remain available.
"""

import json
import warnings
from pathlib import Path
from uuid import uuid4

import pytest

import content_creation.notifications.streaming as streaming_pkg
from content_creation.notifications.streaming import (
    NotificationStreamEvent,
    StreamEventType,
)
from content_creation.platform.observability.service import ObservabilityService


class TestStreamEventModels:
    """Verify retained stream event models function correctly."""

    def test_stream_event_types_defined(self) -> None:
        """Verify all expected enum members exist."""
        assert StreamEventType.NOTIFICATION_CREATED.value == "notification_created"
        assert StreamEventType.NOTIFICATION_READ.value == "notification_read"
        assert StreamEventType.NOTIFICATION_ARCHIVED.value == "notification_archived"
        assert StreamEventType.NOTIFICATION_DELETED.value == "notification_deleted"
        assert StreamEventType.UNREAD_COUNT_UPDATED.value == "unread_count_updated"
        assert StreamEventType.SUMMARY_UPDATED.value == "summary_updated"

    def test_notification_stream_event_serialization(self) -> None:
        """Verify NotificationStreamEvent to_sse_data serialization."""
        notif_id = uuid4()
        event = NotificationStreamEvent(
            event_type=StreamEventType.NOTIFICATION_CREATED,
            notification_id=notif_id,
            category="pipeline",
            severity="info",
            title="Pipeline Started",
            message="Topic generation started",
            payload={"topic_count": 5},
        )
        assert event.to_sse_event() == "notification_created"

        sse_data = event.to_sse_data()
        parsed = json.loads(sse_data)
        assert parsed["event_type"] == "notification_created"
        assert parsed["notification_id"] == str(notif_id)
        assert parsed["category"] == "pipeline"
        assert parsed["title"] == "Pipeline Started"
        assert parsed["payload"] == {"topic_count": 5}

    def test_zero_deprecation_warnings_on_models(self) -> None:
        """Ensure model instantiation produces zero deprecation warnings."""
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            _ = NotificationStreamEvent()
            assert len(recorded) == 0


class TestSSEStreamingRetiral:
    """Verify deprecated SSE streaming stubs are cleanly retired per ADR-001."""

    def test_deprecated_streaming_components_not_exported(self) -> None:
        """Verify retired streaming components are not in __all__ or streaming_pkg."""
        assert not hasattr(streaming_pkg, "ConnectionManager")
        assert not hasattr(streaming_pkg, "NotificationPublisher")
        assert not hasattr(streaming_pkg, "NotificationSSEServer")
        assert "ConnectionManager" not in streaming_pkg.__all__
        assert "NotificationPublisher" not in streaming_pkg.__all__
        assert "NotificationSSEServer" not in streaming_pkg.__all__

    def test_retired_module_imports_raise_importerror(self) -> None:
        """Verify importing deleted modules raises ModuleNotFoundError."""
        with pytest.raises(ModuleNotFoundError):
            import content_creation.notifications.streaming.server  # noqa: F401

        with pytest.raises(ModuleNotFoundError):
            import content_creation.notifications.streaming.connection_manager  # noqa: F401

        with pytest.raises(ModuleNotFoundError):
            import content_creation.notifications.streaming.publisher  # noqa: F401

    def test_observability_snapshot_with_null_connection_manager(self) -> None:
        """Verify ObservabilityService produces snapshot cleanly with connection_manager=None."""
        service = ObservabilityService(connection_manager=None)
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            snapshot = service.snapshot()
            assert snapshot is not None
            assert len(recorded) == 0

    @pytest.mark.parametrize("symbol", ["ConnectionManager", "NotificationPublisher", "NotificationSSEServer"])
    def test_direct_symbol_import_raises_importerror(self, symbol: str) -> None:
        """Covers ERR-004 & DEAD-004: Direct named import of retired SSE classes raises ImportError."""
        with pytest.raises(ImportError):
            exec(f"from content_creation.notifications.streaming import {symbol}")

    @pytest.mark.parametrize("symbol", ["ConnectionManager", "NotificationPublisher", "NotificationSSEServer"])
    def test_getattr_access_raises_attribute_error(self, symbol: str) -> None:
        """Covers ERR-004 & DEAD-004: Attribute access on streaming package raises AttributeError."""
        with pytest.raises(AttributeError):
            getattr(streaming_pkg, symbol)

    def test_service_client_snapshot_zero_deprecation_warnings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Covers ERR-004: ServiceClient.get_operations_snapshot runs with 0 deprecation warnings."""
        from content_creation.platform.storage.database import init_content_factory_db
        from content_creation.ui.services.client import (
            ServiceClient,
            get_context,
            get_notification_db,
        )

        get_context.clear()
        get_notification_db.clear()
        monkeypatch.setenv("CONTENT_FACTORY_ROOT", str(tmp_path))
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        init_content_factory_db(tmp_path / "data" / "content_factory.db")

        client = ServiceClient()
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            snapshot = client.get_operations_snapshot()
            assert snapshot is not None
            deprecation_warnings = [
                w for w in recorded
                if issubclass(w.category, (DeprecationWarning, PendingDeprecationWarning))
            ]
            assert len(deprecation_warnings) == 0, f"Found unexpected deprecation warnings: {deprecation_warnings}"

