"""Event dispatcher integrating subscribers with the event bus under failure isolation."""

import logging
import time
from typing import Callable, Dict, List, Optional

from content_creation.events.bus import EventBus, get_event_bus
from content_creation.events.models import EventType, WorkflowEvent
from content_creation.subscribers.models import (
    EventFilter,
    SubscriberExecutionResult,
    Subscription,
)

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Manages subscriber registration on an EventBus and dispatches events with failure isolation.

    Guarantees:
    - Subscriber failures never stop event delivery to other subscribers.
    - Subscriber failures never crash the publisher or worker.
    - Each subscriber execution is wrapped with timing and exception capture.
    """

    def __init__(self, bus: Optional[EventBus] = None) -> None:
        self._bus = bus or get_event_bus()
        self._subscriptions: Dict[str, Subscription] = {}
        self._callbacks: Dict[str, Callable[[WorkflowEvent], None]] = {}
        self._execution_results: List[SubscriberExecutionResult] = []

    @property
    def execution_results(self) -> List[SubscriberExecutionResult]:
        return list(self._execution_results)

    def _make_registration_key(self, subscription: Subscription) -> str:
        """Create a unique key for a subscription based on subscriber_id and filter."""
        ef = subscription.event_filter
        if ef.event_type is not None:
            return f"{subscription.subscriber_id}:exact:{ef.event_type.value}"
        if ef.category is not None:
            return f"{subscription.subscriber_id}:cat:{ef.category}"
        return f"{subscription.subscriber_id}:wild:*"

    def register(
        self,
        subscription: Subscription,
        callback: Callable[[WorkflowEvent], None],
    ) -> None:
        """Register a subscriber callback on the event bus.

        If the subscription uses an exact event type, subscribes precisely.
        If it uses a category filter, subscribes via wildcard pattern.
        """
        subscriber_id = subscription.subscriber_id
        event_filter = subscription.event_filter
        reg_key = self._make_registration_key(subscription)

        if reg_key in self._subscriptions:
            logger.warning(
                "Registration %s already exists; replacing",
                reg_key,
            )
            self._deregister_key(reg_key)

        wrapped = self._wrap_with_isolation(subscriber_id, callback)

        if event_filter.event_type is not None:
            self._bus.subscribe(event_filter.event_type, wrapped)
            logger.info(
                "Registered subscriber %s for exact event type %s",
                subscriber_id,
                event_filter.event_type.value,
            )
        elif event_filter.category is not None:
            pattern = f"{event_filter.category}.*"
            self._bus.subscribe_wildcard(pattern, wrapped)
            logger.info(
                "Registered subscriber %s for wildcard pattern %s",
                subscriber_id,
                pattern,
            )
        else:
            self._bus.subscribe_wildcard("*", wrapped)
            logger.info(
                "Registered subscriber %s for wildcard pattern *",
                subscriber_id,
            )

        self._subscriptions[reg_key] = subscription
        self._callbacks[reg_key] = wrapped

    def _deregister_key(self, reg_key: str) -> bool:
        """Internal deregistration by registration key."""
        if reg_key not in self._subscriptions:
            return False

        subscription = self._subscriptions[reg_key]
        callback = self._callbacks[reg_key]
        event_filter = subscription.event_filter

        if event_filter.event_type is not None:
            self._bus.unsubscribe(event_filter.event_type, callback)
        elif event_filter.category is not None:
            pattern = f"{event_filter.category}.*"
            self._bus.unsubscribe_wildcard(pattern, callback)
        else:
            self._bus.unsubscribe_wildcard("*", callback)

        del self._subscriptions[reg_key]
        del self._callbacks[reg_key]
        return True

    def deregister(self, subscriber_id: str) -> int:
        """Deregister all registrations for a given subscriber_id.

        Returns the number of registrations removed.
        """
        keys_to_remove = [
            k for k in self._subscriptions
            if k.startswith(f"{subscriber_id}:")
        ]
        for key in keys_to_remove:
            self._deregister_key(key)
            logger.info("Deregistered subscriber registration %s", key)
        return len(keys_to_remove)

    def _wrap_with_isolation(
        self,
        subscriber_id: str,
        callback: Callable[[WorkflowEvent], None],
    ) -> Callable[[WorkflowEvent], None]:
        """Wrap a callback with timing and exception isolation."""

        def isolated_callback(event: WorkflowEvent) -> None:
            start_time = time.monotonic()
            try:
                callback(event)
                duration_ms = (time.monotonic() - start_time) * 1000
                result = SubscriberExecutionResult(
                    subscriber_id=subscriber_id,
                    event_id=event.event_id,
                    execution_duration_ms=duration_ms,
                    success=True,
                )
                self._execution_results.append(result)
            except Exception as e:
                duration_ms = (time.monotonic() - start_time) * 1000
                result = SubscriberExecutionResult(
                    subscriber_id=subscriber_id,
                    event_id=event.event_id,
                    execution_duration_ms=duration_ms,
                    success=False,
                    exception_type=type(e).__name__,
                    exception_message=str(e),
                )
                self._execution_results.append(result)
                logger.exception(
                    "Subscriber %s failed processing event %s: %s",
                    subscriber_id,
                    event.event_id,
                    e,
                )

        return isolated_callback

    def clear_results(self) -> None:
        """Clear accumulated execution results."""
        self._execution_results.clear()
