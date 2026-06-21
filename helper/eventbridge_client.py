"""Shared lazy-init EventBridge client for publisher modules.

Mirrors other_services/eventbridge_client.py from the reference repo.

Why lazy-init:
- The boto3 client is created once per warm Lambda container, not per invocation.
- Importing this module is cheap; the AWS client is only built on first publish.
"""

from __future__ import annotations

from typing import Protocol, cast

import boto3


class _EventBridgeClient(Protocol):
    """Minimal interface for the boto3 EventBridge client (put_events only)."""

    def put_events(self, *, Entries: list[dict[str, str]]) -> dict[str, object]: ...


_events_client: _EventBridgeClient | None = None


def get_events_client(region: str = "us-east-1") -> _EventBridgeClient:
    """Return a process-wide EventBridge client, creating it on first use."""
    global _events_client  # noqa: PLW0603
    if _events_client is None:
        _events_client = cast(_EventBridgeClient, boto3.client("events", region_name=region))
    return _events_client
