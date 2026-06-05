"""SSE HTTP server for real-time notification streaming.

Uses Python's built-in http.server with threading for SSE delivery.
No external dependencies required.

Supports Last-Event-ID header for reconnection replay.
"""

import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from http.server import HTTPServer
from typing import Optional
from urllib.parse import urlparse
from uuid import UUID

from content_creation.notifications.streaming.connection_manager import ConnectionManager
from content_creation.notifications.streaming.models import NotificationStreamEvent

logger = logging.getLogger(__name__)


class _ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTP server that handles each request in a new thread."""
    daemon_threads = True


class _SSERequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for SSE stream endpoint."""

    def do_GET(self) -> None:
        """Handle GET requests for SSE stream."""
        parsed = urlparse(self.path)

        if parsed.path == "/events":
            self._handle_sse_stream()
        elif parsed.path == "/health":
            self._handle_health()
        else:
            self.send_error(404)

    def _handle_health(self) -> None:
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        manager = getattr(self.server, "connection_manager", None)
        data = {
            "status": "ok",
            "clients": manager.active_client_count if manager else 0,
        }
        self.wfile.write(json.dumps(data).encode())

    def _handle_sse_stream(self) -> None:
        """Handle SSE stream connection.

        Supports Last-Event-ID header for reconnection replay.
        """
        manager: Optional[ConnectionManager] = getattr(
            self.server, "connection_manager", None
        )
        if manager is None:
            self.send_error(500, "Connection manager not initialized")
            return

        # Check for Last-Event-ID header (SSE reconnection)
        last_event_id = self.headers.get("Last-Event-ID")

        # Register client
        client = manager.register()

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        try:
            # Send initial connection event
            self._send_sse_event(
                event_type="connected",
                data=json.dumps({
                    "client_id": client.client_id,
                    "message": "Connected to notification stream",
                    "replayed": last_event_id is not None,
                }),
            )

            # Replay missed events if Last-Event-ID was provided
            if last_event_id:
                self._replay_missed_events(last_event_id)

            # Stream events
            heartbeat_interval = ConnectionManager.HEARTBEAT_INTERVAL_SECONDS
            last_heartbeat = time.monotonic()

            while True:
                try:
                    # Wait for event with timeout for heartbeat
                    event = client.event_queue.get(timeout=1.0)

                    if event is None:
                        # Sentinel: client should disconnect
                        break

                    self._send_sse_event(
                        event_type=event.to_sse_event(),
                        data=event.to_sse_data(),
                        event_id=str(event.event_id),
                    )

                except Exception:
                    # Queue timeout — send heartbeat if needed
                    pass

                # Send heartbeat if interval elapsed
                now = time.monotonic()
                if now - last_heartbeat >= heartbeat_interval:
                    self._send_sse_event(
                        event_type="heartbeat",
                        data=json.dumps({"timestamp": time.time()}),
                    )
                    manager.heartbeat(client.client_id)
                    last_heartbeat = now

                    # Check if client is still connected
                    if self.wfile.closed:
                        break

        except (BrokenPipeError, ConnectionResetError, OSError):
            logger.debug("SSE client %s disconnected", client.client_id)
        except Exception as e:
            logger.exception("SSE stream error for client %s: %s", client.client_id, e)
        finally:
            manager.deregister(client.client_id)

    def _send_sse_event(
        self,
        event_type: str,
        data: str,
        event_id: Optional[str] = None,
    ) -> None:
        """Send a single SSE event to the client."""
        lines = []
        if event_id:
            lines.append(f"id: {event_id}")
        lines.append(f"event: {event_type}")
        for line in data.split("\n"):
            lines.append(f"data: {line}")
        lines.append("")
        lines.append("")

        payload = "\n".join(lines).encode("utf-8")
        self.wfile.write(payload)
        self.wfile.flush()

    def _replay_missed_events(self, last_event_id: str) -> None:
        """Replay events after the given Last-Event-ID.

        Uses the event store to find events after the specified ID
        and sends them to the reconnecting client.
        """
        try:
            sse_server = getattr(self.server, "sse_server_ref", None)
            if sse_server is None:
                return

            event_store = getattr(sse_server, "_event_store", None)
            if event_store is None:
                return

            # Parse the last event ID and query for events after it
            from uuid import UUID as _UUID

            try:
                anchor_id = _UUID(last_event_id)
            except ValueError:
                logger.debug("Invalid Last-Event-ID: %s", last_event_id)
                return

            # Query events after the anchor
            missed_records = event_store.list_after_event(anchor_id, limit=100)

            for record in missed_records:
                # Convert EventRecord to NotificationStreamEvent for SSE
                from content_creation.notifications.streaming.models import (
                    StreamEventType,
                )

                payload = record.payload()
                event_type_str = record.event_name

                # Map event names to stream event types
                stream_type = StreamEventType.NOTIFICATION_CREATED
                if "approved" in event_type_str or "rejected" in event_type_str:
                    stream_type = StreamEventType.NOTIFICATION_CREATED
                elif "generated" in event_type_str or "built" in event_type_str:
                    stream_type = StreamEventType.NOTIFICATION_CREATED

                stream_event = NotificationStreamEvent(
                    event_type=stream_type,
                    notification_id=record.event_id,
                    category=payload.get("category", record.category),
                    severity=payload.get("severity", "info"),
                    title=payload.get("title", record.event_name),
                    message=payload.get("message", ""),
                    timestamp=record.created_at,
                    payload=payload,
                )

                self._send_sse_event(
                    event_type=stream_event.to_sse_event(),
                    data=stream_event.to_sse_data(),
                    event_id=str(stream_event.event_id),
                )

            if missed_records:
                logger.info(
                    "Replayed %d events for Last-Event-ID %s",
                    len(missed_records),
                    last_event_id,
                )

        except Exception:
            logger.exception("Error replaying missed events for Last-Event-ID %s", last_event_id)

    def log_message(self, format: str, *args) -> None:
        """Suppress default HTTP request logging."""
        pass


class NotificationSSEServer:
    """SSE server for real-time notification streaming.

    Runs as a background daemon thread. Serves SSE events on a configurable port.

    Usage:
        server = NotificationSSEServer(port=8502)
        server.start()
        # ... server runs in background ...
        server.stop()
    """

    def __init__(
        self,
        connection_manager: Optional[ConnectionManager] = None,
        port: int = 8502,
        host: str = "0.0.0.0",
        event_store: Optional[object] = None,
    ) -> None:
        self._connection_manager = connection_manager or ConnectionManager()
        self._port = port
        self._host = host
        self._event_store = event_store  # EventRepository for Last-Event-ID replay
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        self._started_event = threading.Event()
        self._shutdown_event = threading.Event()

    @property
    def connection_manager(self) -> ConnectionManager:
        return self._connection_manager

    @property
    def port(self) -> int:
        return self._port

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_shutting_down(self) -> bool:
        return self._shutdown_event.is_set()

    def start(self) -> None:
        """Start the SSE server in a background thread."""
        if self._running:
            logger.warning("SSE server already running")
            return

        self._server = _ThreadedHTTPServer((self._host, self._port), _SSERequestHandler)
        self._server.connection_manager = self._connection_manager  # type: ignore
        self._server.sse_server_ref = self  # type: ignore
        self._running = True
        self._shutdown_event.clear()

        self._thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="sse-server",
        )
        self._thread.start()

        # Start cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="sse-cleanup",
        )
        self._cleanup_thread.start()

        # Wait for server to be ready
        self._started_event.wait(timeout=2.0)
        logger.info("SSE server started on %s:%d", self._host, self._port)

    def _run_server(self) -> None:
        """Run the HTTP server and signal when ready."""
        if self._server:
            self._started_event.set()
            self._server.serve_forever()

    def stop(self) -> None:
        """Stop the SSE server."""
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        # Send sentinel to all clients to unblock handlers
        for client in list(self._connection_manager._clients.values()):
            try:
                client.event_queue.put_nowait(None)
            except Exception:
                pass

        if self._server:
            # Give handlers a moment to process sentinels
            time.sleep(0.1)
            self._server.shutdown()
            self._server.server_close()
        logger.info("SSE server stopped")

    def _cleanup_loop(self) -> None:
        """Periodically clean up stale client connections."""
        while self._running:
            time.sleep(ConnectionManager.HEARTBEAT_INTERVAL_SECONDS)
            if self._running:
                cleaned = self._connection_manager.cleanup_stale_clients()
                if cleaned > 0:
                    logger.info("Cleaned up %d stale SSE clients", cleaned)
