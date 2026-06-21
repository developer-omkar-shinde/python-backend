"""Onboarding event consumer — SQS Lambda entry point + router.

This single Lambda consumes two kinds of SQS messages and routes each record
to the right dispatcher by inspecting the message shape:

1. EventBridge-wrapped records (rule -> SQS target). Body looks like:
       {"source": "...", "detail-type": "user.signed_up", "detail": {...}}
   -> dispatched by `detail-type` via eventbridge_handler.

2. SNS/SQS domain events (topic -> SQS subscription). Body is an SNS envelope
   whose Message is a flat domain event:
       {"event_type": "UserCreated", "user_id": "...", ...}
   -> dispatched by `event_type` via the queue-handler registry.

Routing by shape (not by queue) keeps one entry point while still letting each
source type have isolated handlers — the same idea as the reference repo's
bonus_service_v2 router.
"""

from __future__ import annotations

import json

from . import logger
from . import handler  # noqa: F401 — registers @register_queue_event handlers at import
from . import eventbridge_handler  # noqa: F401 — registers @register_eventbridge_event handlers
from .eventbridge_handler import dispatch_eventbridge_records
from .registry import registry


def _is_eventbridge_envelope(body: dict) -> bool:
    """EventBridge events always carry both `detail-type` and `detail`."""
    return "detail-type" in body and "detail" in body


def _dispatch_domain_event(body: dict) -> None:
    """Handle an SNS-wrapped (or raw) flat domain event keyed by event_type."""
    message = json.loads(body["Message"]) if "Message" in body else body
    event_type = message.get("event_type", "")

    handler_fn = registry.get_queue_handler(event_type)
    if handler_fn:
        logger.info("Dispatching event: %s", event_type)
        handler_fn(message)
    else:
        logger.info("Ignoring event_type=%s", event_type)


def lambda_handler(event, context):
    """Route each SQS record by shape.

    If any record is an EventBridge envelope, the whole batch is processed by
    the EventBridge dispatcher (which returns a partial-batch response). This
    keeps EventBridge and SNS/SQS queues on separate event source mappings in
    practice, while still supporting both here for learning.
    """
    records = event.get("Records", [])
    if records and _is_eventbridge_envelope(json.loads(records[0].get("body", "{}"))):
        return dispatch_eventbridge_records(event)

    for record in records:
        try:
            body = json.loads(record["body"])
            _dispatch_domain_event(body)
        except Exception:
            logger.exception("Failed to process onboarding event record")
            raise  # Let SQS retry the whole batch for plain domain events
