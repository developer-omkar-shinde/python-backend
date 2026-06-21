"""EventBridge ingress handlers for the onboarding consumer Lambda.

EventBridge events reach this Lambda via an SQS queue (EventBridge rule ->
SQS target). Each SQS record body is the full EventBridge envelope:

    {
      "source":      "onboarding.service",
      "detail-type": "user.signed_up",
      "detail":      { "user_id": "...", "country": "GH", ... }
    }

`dispatch_eventbridge_records` unwraps each envelope and routes by `detail-type`
to a handler registered with @registry.register_eventbridge_event(...).

Partial-batch semantics: failed records are returned as `batchItemFailures` so
SQS retries only those records, not the whole batch.
"""

from __future__ import annotations

import json

from . import logger
from .registry import registry


@registry.register_eventbridge_event("user.signed_up")
def on_user_signed_up(detail: dict) -> None:
    """React to a new sign-up routed from EventBridge."""
    logger.info(
        "EventBridge user.signed_up — user_id=%s country=%s email=%s",
        detail.get("user_id", ""),
        detail.get("country", ""),
        detail.get("email", ""),
    )
    # TODO: send welcome email / initialize preferences


@registry.register_eventbridge_event("kyc.approved")
def on_kyc_approved(detail: dict) -> None:
    """React to a KYC approval routed from EventBridge."""
    logger.info(
        "EventBridge kyc.approved — user_id=%s country=%s tier=%s",
        detail.get("user_id", ""),
        detail.get("country", ""),
        detail.get("tier", ""),
    )
    # TODO: unlock features for approved tier


def dispatch_eventbridge_records(event: dict) -> dict:
    """Process SQS records that carry EventBridge envelopes.

    Returns an SQS partial-batch response: only failed records are reported,
    so successful records are not redelivered.
    """
    failures: list[str] = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "")
        try:
            envelope = json.loads(record["body"])
            detail_type = envelope.get("detail-type", "")
            detail = envelope.get("detail") or {}

            handler_fn = registry.get_eventbridge_handler(detail_type)
            if handler_fn is None:
                logger.info("No EventBridge handler for detail-type=%s; skipping", detail_type)
                continue

            logger.info("Dispatching EventBridge detail-type=%s", detail_type)
            handler_fn(detail)
        except Exception:
            logger.exception("Failed to process EventBridge record messageId=%s", message_id)
            if message_id:
                failures.append(message_id)

    return {"batchItemFailures": [{"itemIdentifier": mid} for mid in failures]}
