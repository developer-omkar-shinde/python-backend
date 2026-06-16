"""Module self-registration registry.

Modules call @registry.register_queue_event("EventType") on their handler
functions at import time. The Lambda entry point looks up handlers by event_type.

Adding a new event type: register a handler function in handler.py.
Zero other files change.

Mirrors bonus_platform_service/bonus_service_v2/registry.py from the reference repo.
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
        """Decorator — registers a function as handler for the given event_type.

        Usage:
            @registry.register_queue_event("UserCreated")
            def handle_user_created(data: dict) -> None:
                ...
        """
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
