"""Module self-registration registry for email service.

Mirrors onboarding/registry.py pattern.
"""

from __future__ import annotations

from collections.abc import Callable

from helper.utilities import get_logger

logger = get_logger(__name__)


class DuplicateHandlerError(ValueError):
    """Raised when a handler is registered for an event type that already has one."""


class ModuleRegistry:
    def __init__(self) -> None:
        self._queue_handlers: dict[str, Callable] = {}

    def register_queue_event(self, event_type: str) -> Callable:
        """Decorator — registers a function as handler for the given event_type."""
        def decorator(fn: Callable) -> Callable:
            if event_type in self._queue_handlers:
                raise DuplicateHandlerError(event_type)
            self._queue_handlers[event_type] = fn
            logger.debug("Registered queue handler: %s -> %s", event_type, fn.__qualname__)
            return fn
        return decorator

    def get_queue_handler(self, event_type: str) -> Callable | None:
        return self._queue_handlers.get(event_type)

    def registered_queue_events(self) -> list[str]:
        return list(self._queue_handlers.keys())

    def clear(self) -> None:
        """Reset all registrations. Used in tests."""
        self._queue_handlers.clear()


registry = ModuleRegistry()
