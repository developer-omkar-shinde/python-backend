"""Onboarding event consumer — SQS Lambda handler."""

from __future__ import annotations

import json

from . import logger
from . import handler  # noqa: F401 — registers all @registry.register_queue_event handlers
from .registry import registry


def lambda_handler(event, context):
    """Process SQS messages containing SNS-wrapped onboarding domain events.

    Dispatches each record to the registered handler via registry.get_queue_handler().
    Unknown event types are logged and skipped.
    Exceptions raise — letting SQS retry the record.
    """
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])

            # Unwrap SNS envelope if present
            message = json.loads(body["Message"]) if "Message" in body else body

            event_type = message.get("event_type", "")

            handler_fn = registry.get_queue_handler(event_type)
            if handler_fn:
                logger.info("Dispatching event: %s", event_type)
                handler_fn(message)
            else:
                logger.info("Ignoring event_type=%s", event_type)

        except Exception:
            logger.exception("Failed to process onboarding event record")
            raise  # Let SQS retry
