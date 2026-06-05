"""Connection manager for tracking SSE clients and broadcasting events."""

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional
from uuid import uuid4

from content_creation.notifications.streaming.models import NotificationStreamEvent

logger = logging.getLogger(__name__)


@dataclass
class ClientInfo:
    """Tracks a connected SSE client."""

    client_id: str
    connected_at: datetime
    last_heartbeat: datetime
    event_queue: "queue.Queue[Optional[NotificationStreamEvent]]" = field(
        default_factory=lambda: __import__("queue").Queue(maxsize=256)
    )


class ConnectionManager:
    """Manages SSE client connections and event broadcasting.

    Responsibilities:
    - Client registration and deregistration
    - Connection tracking with timestamps
    - Event broadcast to all connected clients
    - Heartbeat support for keepalive
    - Stale client cleanup

    Thread-safe. No Streamlit, worker, or UI imports.
    """

    HEARTBEAT_INTERVAL_SECONDS = 30
    CLIENT_TIMEOUT_SECONDS = 90

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._clients: OrderedDict[str, ClientInfo] = OrderedDict()
        self._event_counter: int = 0

    @property
    def active_client_count(self) -> int:
        """Return the number of active connected clients."""
        with self._lock:
            return len(self._clients)

    def register(self) -> ClientInfo:
        """Register a new SSE client and return its info."""
        client_id = str(uuid4())
        now = datetime.now(timezone.utc)
        client = ClientInfo(
            client_id=client_id,
            connected_at=now,
            last_heartbeat=now,
        )
        with self._lock:
            self._clients[client_id] = client
        logger.info("SSE client connected: %s (total: %d)", client_id, self.active_client_count)
        return client

    def deregister(self, client_id: str) -> None:
        """Deregister an SSE client."""
        with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                logger.info(
                    "SSE client disconnected: %s (total: %d)",
                    client_id,
                    self.active_client_count,
                )

    def heartbeat(self, client_id: str) -> None:
        """Update the heartbeat timestamp for a client."""
        with self._lock:
            if client_id in self._clients:
                self._clients[client_id].last_heartbeat = datetime.now(timezone.utc)

    def broadcast(self, event: NotificationStreamEvent) -> int:
        """Broadcast an event to all connected clients.

        Returns the number of clients that received the event.
        """
        delivered = 0
        with self._lock:
            clients = list(self._clients.values())

        for client in clients:
            try:
                client.event_queue.put_nowait(event)
                delivered += 1
            except Exception:
                logger.warning(
                    "Failed to deliver event to client %s (queue full)",
                    client.client_id,
                )

        self._event_counter += 1
        return delivered

    def cleanup_stale_clients(self) -> int:
        """Remove clients that have not sent a heartbeat within timeout.

        Returns the number of clients removed.
        """
        now = datetime.now(timezone.utc)
        stale_ids: List[str] = []

        with self._lock:
            for client_id, client in self._clients.items():
                elapsed = (now - client.last_heartbeat).total_seconds()
                if elapsed > self.CLIENT_TIMEOUT_SECONDS:
                    stale_ids.append(client_id)

        for client_id in stale_ids:
            self.deregister(client_id)
            logger.info("Cleaned up stale SSE client: %s", client_id)

        return len(stale_ids)

    def get_client(self, client_id: str) -> Optional[ClientInfo]:
        """Retrieve client info by ID."""
        with self._lock:
            return self._clients.get(client_id)

    @property
    def event_counter(self) -> int:
        """Total events broadcast since manager creation."""
        return self._event_counter
