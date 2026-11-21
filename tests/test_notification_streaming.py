"""Comprehensive tests for Phase 11.8.5 — SSE Streaming Infrastructure."""

import json
import socket
import sqlite3
import threading
import time
from datetime import datetime, timezone
from http.client import HTTPConnection
from typing import List
from unittest.mock import MagicMock
from uuid import uuid4

import pytest


def _local_sockets_available() -> bool:
    """Return whether this environment permits binding local test sockets."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", 0))
        finally:
            sock.close()
    except OSError:
        return False
    return True


requires_local_socket = pytest.mark.skipif(
    not _local_sockets_available(),
    reason="local socket creation is unavailable in this test environment",
)


def _sse_connect_and_read(port: int, read_timeout: float = 2.0) -> tuple:
    """Connect to SSE endpoint and read initial data with timeout.

    Returns (socket, initial_data) or raises on failure.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect(("localhost", port))

    # Send HTTP request
    request = b"GET /events HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
    sock.sendall(request)

    # Read response status line
    status_line = b""
    while b"\r\n" not in status_line:
        chunk = sock.recv(1)
        if not chunk:
            break
        status_line += chunk

    # Read headers until empty line
    headers = b""
    while True:
        line = b""
        while b"\r\n" not in line:
            chunk = sock.recv(1)
            if not chunk:
                break
            line += chunk
        headers += line
        if line == b"\r\n":
            break

    # Read initial SSE data with timeout
    sock.settimeout(read_timeout)
    initial_data = b""
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            initial_data += chunk
    except (socket.timeout, BlockingIOError):
        pass

    return sock, initial_data.decode(errors="replace")


from content_creation.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)
from content_creation.notifications.schema import create_notification_schema
from content_creation.notifications.sqlite_repository import (
    SQLiteNotificationRepository,
)
from content_creation.notifications.streaming.connection_manager import (
    ConnectionManager,
)
from content_creation.notifications.streaming.models import (
    NotificationStreamEvent,
    StreamEventType,
)
from content_creation.notifications.streaming.publisher import NotificationPublisher
from content_creation.notifications.streaming.server import NotificationSSEServer

# ======================================================================
# FIXTURES
# ======================================================================


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    create_notification_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def repo(db_conn: sqlite3.Connection) -> SQLiteNotificationRepository:
    return SQLiteNotificationRepository(db_conn)


@pytest.fixture
def manager() -> ConnectionManager:
    return ConnectionManager()


@pytest.fixture
def publisher(
    repo: SQLiteNotificationRepository, manager: ConnectionManager
) -> NotificationPublisher:
    return NotificationPublisher(repo, manager)


def _make_notification(
    title: str = "Test",
    severity: NotificationSeverity = NotificationSeverity.INFO,
    category: NotificationCategory = NotificationCategory.WORKFLOW,
    status: NotificationStatus = NotificationStatus.UNREAD,
) -> Notification:
    return Notification(
        notification_id=uuid4(),
        title=title,
        message="Test message",
        severity=severity,
        category=category,
        status=status,
        timestamp=datetime.now(timezone.utc),
        correlation_id="corr-1",
        event_id=uuid4(),
    )


# ======================================================================
# PART 3: STREAM EVENT MODEL TESTS
# ======================================================================


class TestNotificationStreamEvent:
    def test_creation(self) -> None:
        evt = NotificationStreamEvent(
            event_type=StreamEventType.NOTIFICATION_CREATED,
            notification_id=uuid4(),
            category="WORKFLOW",
            severity="INFO",
            title="Test",
            message="Test msg",
        )
        assert evt.event_type == StreamEventType.NOTIFICATION_CREATED
        assert evt.category == "WORKFLOW"
        assert isinstance(evt.event_id, type(uuid4()))

    def test_to_sse_data(self) -> None:
        nid = uuid4()
        evt = NotificationStreamEvent(
            event_type=StreamEventType.NOTIFICATION_CREATED,
            notification_id=nid,
            category="JOB",
            severity="ERROR",
            title="Failed",
            message="Job failed",
        )
        data_str = evt.to_sse_data()
        data = json.loads(data_str)
        assert data["event_type"] == "notification_created"
        assert data["notification_id"] == str(nid)
        assert data["category"] == "JOB"
        assert data["severity"] == "ERROR"
        assert data["title"] == "Failed"

    def test_to_sse_event(self) -> None:
        evt = NotificationStreamEvent(event_type=StreamEventType.UNREAD_COUNT_UPDATED)
        assert evt.to_sse_event() == "unread_count_updated"

    def test_immutable(self) -> None:
        evt = NotificationStreamEvent(title="Test")
        with pytest.raises(AttributeError):
            evt.title = "New"  # type: ignore

    def test_default_values(self) -> None:
        evt = NotificationStreamEvent()
        assert evt.event_type == StreamEventType.NOTIFICATION_CREATED
        assert evt.payload == {}
        assert evt.category == ""
        assert evt.notification_id is None


class TestStreamEventType:
    def test_values(self) -> None:
        assert StreamEventType.NOTIFICATION_CREATED.value == "notification_created"
        assert StreamEventType.NOTIFICATION_READ.value == "notification_read"
        assert StreamEventType.NOTIFICATION_ARCHIVED.value == "notification_archived"
        assert StreamEventType.NOTIFICATION_DELETED.value == "notification_deleted"
        assert StreamEventType.UNREAD_COUNT_UPDATED.value == "unread_count_updated"
        assert StreamEventType.SUMMARY_UPDATED.value == "summary_updated"


# ======================================================================
# PART 5: CONNECTION MANAGER TESTS
# ======================================================================


class TestConnectionManager:
    def test_register(self, manager: ConnectionManager) -> None:
        client = manager.register()
        assert client.client_id is not None
        assert manager.active_client_count == 1

    def test_deregister(self, manager: ConnectionManager) -> None:
        client = manager.register()
        assert manager.active_client_count == 1
        manager.deregister(client.client_id)
        assert manager.active_client_count == 0

    def test_deregister_nonexistent(self, manager: ConnectionManager) -> None:
        manager.deregister("nonexistent-id")
        assert manager.active_client_count == 0

    def test_heartbeat(self, manager: ConnectionManager) -> None:
        client = manager.register()
        old_heartbeat = client.last_heartbeat
        time.sleep(0.01)
        manager.heartbeat(client.client_id)
        updated = manager.get_client(client.client_id)
        assert updated is not None
        assert updated.last_heartbeat >= old_heartbeat

    def test_broadcast(self, manager: ConnectionManager) -> None:
        client = manager.register()
        evt = NotificationStreamEvent(
            event_type=StreamEventType.NOTIFICATION_CREATED,
            title="Test",
        )
        delivered = manager.broadcast(evt)
        assert delivered == 1
        assert not client.event_queue.empty()
        received = client.event_queue.get_nowait()
        assert received.title == "Test"

    def test_broadcast_to_multiple_clients(self, manager: ConnectionManager) -> None:
        c1 = manager.register()
        c2 = manager.register()
        c3 = manager.register()
        evt = NotificationStreamEvent(event_type=StreamEventType.NOTIFICATION_CREATED)
        delivered = manager.broadcast(evt)
        assert delivered == 3
        assert not c1.event_queue.empty()
        assert not c2.event_queue.empty()
        assert not c3.event_queue.empty()

    def test_broadcast_no_clients(self, manager: ConnectionManager) -> None:
        evt = NotificationStreamEvent(event_type=StreamEventType.NOTIFICATION_CREATED)
        delivered = manager.broadcast(evt)
        assert delivered == 0

    def test_cleanup_stale_clients(self, manager: ConnectionManager) -> None:
        client = manager.register()
        # Simulate stale client by backdating heartbeat
        client.last_heartbeat = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0
        )
        cleaned = manager.cleanup_stale_clients()
        assert cleaned == 1
        assert manager.active_client_count == 0

    def test_cleanup_keeps_active_clients(self, manager: ConnectionManager) -> None:
        client = manager.register()
        manager.heartbeat(client.client_id)
        cleaned = manager.cleanup_stale_clients()
        assert cleaned == 0
        assert manager.active_client_count == 1

    def test_event_counter(self, manager: ConnectionManager) -> None:
        assert manager.event_counter == 0
        manager.broadcast(NotificationStreamEvent())
        assert manager.event_counter == 1
        manager.broadcast(NotificationStreamEvent())
        assert manager.event_counter == 2

    def test_get_client(self, manager: ConnectionManager) -> None:
        client = manager.register()
        fetched = manager.get_client(client.client_id)
        assert fetched is not None
        assert fetched.client_id == client.client_id

    def test_get_client_nonexistent(self, manager: ConnectionManager) -> None:
        assert manager.get_client("nope") is None


# ======================================================================
# PART 4: NOTIFICATION PUBLISHER TESTS
# ======================================================================


class TestNotificationPublisher:
    def test_on_notification_created(
        self,
        publisher: NotificationPublisher,
        manager: ConnectionManager,
        repo: SQLiteNotificationRepository,
    ) -> None:
        client = manager.register()
        n = _make_notification(title="New Alert")
        repo.create_notification(n)

        publisher.on_notification_created(n)

        assert not client.event_queue.empty()
        event = client.event_queue.get_nowait()
        assert event.event_type == StreamEventType.NOTIFICATION_CREATED
        assert event.title == "New Alert"

    def test_on_notification_created_broadcasts_unread_count(
        self,
        publisher: NotificationPublisher,
        manager: ConnectionManager,
        repo: SQLiteNotificationRepository,
    ) -> None:
        client = manager.register()
        n = _make_notification()
        repo.create_notification(n)

        publisher.on_notification_created(n)

        # Should receive 2 events: notification_created + unread_count_updated
        events = []
        while not client.event_queue.empty():
            events.append(client.event_queue.get_nowait())
        assert len(events) == 2
        assert events[0].event_type == StreamEventType.NOTIFICATION_CREATED
        assert events[1].event_type == StreamEventType.UNREAD_COUNT_UPDATED
        assert events[1].payload["unread_count"] == 1

    def test_on_notification_read(
        self,
        publisher: NotificationPublisher,
        manager: ConnectionManager,
        repo: SQLiteNotificationRepository,
    ) -> None:
        client = manager.register()
        n = _make_notification()
        repo.create_notification(n)

        publisher.on_notification_read(n.notification_id)

        events = []
        while not client.event_queue.empty():
            events.append(client.event_queue.get_nowait())
        read_events = [
            e for e in events if e.event_type == StreamEventType.NOTIFICATION_READ
        ]
        assert len(read_events) == 1

    def test_on_notification_archived(
        self,
        publisher: NotificationPublisher,
        manager: ConnectionManager,
        repo: SQLiteNotificationRepository,
    ) -> None:
        client = manager.register()
        n = _make_notification()
        repo.create_notification(n)

        publisher.on_notification_archived(n.notification_id)

        events = []
        while not client.event_queue.empty():
            events.append(client.event_queue.get_nowait())
        archive_events = [
            e for e in events if e.event_type == StreamEventType.NOTIFICATION_ARCHIVED
        ]
        assert len(archive_events) == 1

    def test_publisher_does_not_mutate_state(
        self,
        publisher: NotificationPublisher,
        repo: SQLiteNotificationRepository,
    ) -> None:
        n = _make_notification(status=NotificationStatus.UNREAD)
        repo.create_notification(n)

        publisher.on_notification_created(n)

        fetched = repo.get_notification(n.notification_id)
        assert fetched is not None
        assert fetched.status == NotificationStatus.UNREAD

    def test_broadcast_unread_count(
        self,
        publisher: NotificationPublisher,
        manager: ConnectionManager,
        repo: SQLiteNotificationRepository,
    ) -> None:
        client = manager.register()
        repo.create_notification(_make_notification())
        repo.create_notification(_make_notification())

        publisher.broadcast_unread_count()

        event = client.event_queue.get_nowait()
        assert event.event_type == StreamEventType.UNREAD_COUNT_UPDATED
        assert event.payload["unread_count"] == 2

    def test_broadcast_summary_update(
        self,
        publisher: NotificationPublisher,
        manager: ConnectionManager,
    ) -> None:
        client = manager.register()
        publisher.broadcast_summary_update()

        event = client.event_queue.get_nowait()
        assert event.event_type == StreamEventType.SUMMARY_UPDATED


# ======================================================================
# PART 6: SSE SERVER TESTS
# ======================================================================


class TestNotificationSSEServer:
    @requires_local_socket
    def test_server_start_stop(self) -> None:
        server = NotificationSSEServer(port=18502)
        server.start()
        assert server.is_running is True
        time.sleep(0.1)
        server.stop()
        assert server.is_running is False

    @requires_local_socket
    def test_server_cleanup_loop(self) -> None:
        """Test cleanup loop removes stale clients."""
        manager = ConnectionManager()
        server = NotificationSSEServer(connection_manager=manager, port=18509)
        server.start()
        try:
            time.sleep(0.2)
            # Register a client directly with old heartbeat
            client = manager.register()
            # Make it stale by setting last_heartbeat to far past
            client.last_heartbeat = datetime(2020, 1, 1, tzinfo=timezone.utc)

            # Run cleanup
            cleaned = manager.cleanup_stale_clients()
            assert cleaned == 1
            assert manager.active_client_count == 0
        finally:
            server.stop()

    @requires_local_socket
    def test_server_shutdown_event(self) -> None:
        """Test server shutdown event is set on stop."""
        server = NotificationSSEServer(port=18513)
        assert server.is_shutting_down is False
        server.start()
        time.sleep(0.1)
        server.stop()
        assert server.is_shutting_down is True

    @requires_local_socket
    def test_server_already_running(self) -> None:
        """Test starting server when already running."""
        server = NotificationSSEServer(port=18514)
        server.start()
        try:
            time.sleep(0.1)
            # Should log warning and return
            server.start()
            assert server.is_running is True
        finally:
            server.stop()

    def test_server_already_stopped(self) -> None:
        """Test stopping server when already stopped."""
        server = NotificationSSEServer(port=18515)
        # Should return without error
        server.stop()
        assert server.is_running is False

