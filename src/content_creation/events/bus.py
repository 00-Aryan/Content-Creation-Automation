"""Event Bus interfaces and thread-safe In-Memory Event Bus implementation."""

from abc import ABC, abstractmethod
import fnmatch
import logging
import threading
from typing import Callable, Dict, List, Union

from content_creation.events.models import EventType, WorkflowEvent

logger = logging.getLogger(__name__)

# Map EventTypes to their canonical categories to support category-based pattern matching (e.g. "workflow.*")
EVENT_TYPE_CATEGORIES: Dict[EventType, str] = {
    EventType.BRIEF_GENERATED: "workflow",
    EventType.CI_GENERATED: "workflow",
    EventType.STORYBOARD_GENERATED: "workflow",
    EventType.ASSET_GENERATED: "workflow",
    EventType.MANIFEST_BUILT: "workflow",

    EventType.BRIEF_APPROVED: "review",
    EventType.BRIEF_REJECTED: "review",
    EventType.STORYBOARD_APPROVED: "review",
    EventType.STORYBOARD_REJECTED: "review",
    EventType.ASSET_APPROVED: "review",
    EventType.ASSET_REJECTED: "review",

    EventType.JOB_CREATED: "job",
    EventType.JOB_QUEUED: "job",
    EventType.JOB_STARTED: "job",
    EventType.JOB_COMPLETED: "job",
    EventType.JOB_FAILED: "job",
    EventType.JOB_CANCELLED: "job",
    EventType.JOB_RETRIED: "job",

    EventType.LOCK_ACQUIRED: "lock",
    EventType.LOCK_RELEASED: "lock",
    EventType.LOCK_EXPIRED: "lock",

    EventType.ZOMBIE_JOB_RECOVERED: "recovery",
    EventType.STALE_LOCK_EXPIRED: "recovery",

    EventType.PIPELINE_STARTED: "pipeline",
    EventType.PIPELINE_COMPLETED: "pipeline",
    EventType.PIPELINE_FAILED: "pipeline",
}


class EventPublisher(ABC):
    """Abstract interface defining the event publishing contract."""

    @abstractmethod
    def publish(self, event: WorkflowEvent) -> None:
        """Publish an event to the bus."""
        pass


class EventSubscriber(ABC):
    """Abstract interface defining subscription management for events."""

    @abstractmethod
    def subscribe(self, event_type: Union[EventType, str], callback: Callable[[WorkflowEvent], None]) -> None:
        """Subscribe a callback to a specific EventType."""
        pass

    @abstractmethod
    def unsubscribe(self, event_type: Union[EventType, str], callback: Callable[[WorkflowEvent], None]) -> None:
        """Unsubscribe a callback from a specific EventType."""
        pass

    @abstractmethod
    def subscribe_wildcard(self, pattern: str, callback: Callable[[WorkflowEvent], None]) -> None:
        """Subscribe to events matching a wildcard pattern (e.g. 'job.*')."""
        pass

    @abstractmethod
    def unsubscribe_wildcard(self, pattern: str, callback: Callable[[WorkflowEvent], None]) -> None:
        """Unsubscribe a callback from a wildcard pattern."""
        pass


class EventBus(EventPublisher, EventSubscriber, ABC):
    """Combined Event Bus interface acting as both publisher and subscriber broker."""

    pass


class InMemoryEventBus(EventBus):
    """Thread-safe, synchronous, in-process Event Bus implementing wildcard and exact routing."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._exact_listeners: Dict[str, List[Callable[[WorkflowEvent], None]]] = {}
        self._wildcard_listeners: Dict[str, List[Callable[[WorkflowEvent], None]]] = {}

    def subscribe(self, event_type: Union[EventType, str], callback: Callable[[WorkflowEvent], None]) -> None:
        etype = event_type.value if isinstance(event_type, EventType) else str(event_type)
        with self._lock:
            if etype not in self._exact_listeners:
                self._exact_listeners[etype] = []
            if callback not in self._exact_listeners[etype]:
                self._exact_listeners[etype].append(callback)

    def unsubscribe(self, event_type: Union[EventType, str], callback: Callable[[WorkflowEvent], None]) -> None:
        etype = event_type.value if isinstance(event_type, EventType) else str(event_type)
        with self._lock:
            if etype in self._exact_listeners and callback in self._exact_listeners[etype]:
                self._exact_listeners[etype].remove(callback)

    def subscribe_wildcard(self, pattern: str, callback: Callable[[WorkflowEvent], None]) -> None:
        with self._lock:
            if pattern not in self._wildcard_listeners:
                self._wildcard_listeners[pattern] = []
            if callback not in self._wildcard_listeners[pattern]:
                self._wildcard_listeners[pattern].append(callback)

    def unsubscribe_wildcard(self, pattern: str, callback: Callable[[WorkflowEvent], None]) -> None:
        with self._lock:
            if pattern in self._wildcard_listeners and callback in self._wildcard_listeners[pattern]:
                self._wildcard_listeners[pattern].remove(callback)

    def _event_matches_pattern(self, event: WorkflowEvent, pattern: str) -> bool:
        """Evaluate if an event matches a wildcard pattern based on prefix or category mapping."""
        event_name = event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type)

        # 1. Category mapping checks (e.g. "workflow.*" matches "brief_generated")
        category = EVENT_TYPE_CATEGORIES.get(event.event_type) if isinstance(event.event_type, EventType) else None
        if category and pattern == f"{category}.*":
            return True

        # 2. General fnmatch check
        if fnmatch.fnmatch(event_name, pattern):
            return True

        # 3. Handle translated prefix matching (e.g., "job.*" matches "job_created")
        translated_pattern = pattern.replace(".", "_")
        if fnmatch.fnmatch(event_name, translated_pattern):
            return True

        # 4. Fallback explicit start checks
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            if event_name.startswith(prefix + "_") or event_name.startswith(prefix + "."):
                return True

        return False

    def publish(self, event: WorkflowEvent) -> None:
        """Publish event synchronously to all registered listeners. 
        
        Isolates subscriber errors: an exception in one callback will not stall execution of others.
        """
        etype = event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type)
        callbacks_to_run: List[Callable[[WorkflowEvent], None]] = []

        with self._lock:
            # Gather exact subscribers
            if etype in self._exact_listeners:
                callbacks_to_run.extend(self._exact_listeners[etype])

            # Gather wildcard subscribers
            for pattern, list_callbacks in self._wildcard_listeners.items():
                if self._event_matches_pattern(event, pattern):
                    callbacks_to_run.extend(list_callbacks)

        # Execute callbacks outside of the lock scope to prevent deadlocks from recursive calls
        for callback in callbacks_to_run:
            try:
                callback(event)
            except Exception as e:
                logger.exception(f"Exception raised in subscriber callback {callback} for event {etype}: {e}")


# Define default global Event Bus
_default_bus = InMemoryEventBus()


def get_event_bus() -> EventBus:
    """Retrieve the global default EventBus broker."""
    return _default_bus
