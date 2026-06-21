"""Publish typed business events to a custom AWS EventBridge bus.

Mirrors other_services/business_event_publisher.py from the reference repo.

Flow:
    onboarding service  ->  publish_business_event(UserSignedUp(...))
                        ->  EventBridge put_events on the custom bus
                        ->  rules route by source / detail-type / detail fields
                        ->  SQS queues  ->  consumer Lambdas

Design choices (matching the reference):
- One `Entries` item per call (batch up to 10 if needed).
- Detail is JSON-serialized; `default=str` keeps it robust to dates/Decimals.
- Returns a bool instead of raising, so a publish failure never breaks the
  caller's main flow. Failures are logged for alerting.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from helper.eventbridge_client import get_events_client
from helper.utilities import get_logger

if TYPE_CHECKING:
    from helper.business_events import BusinessEvent

logger = get_logger(__name__)

# Custom bus name; overridable per environment via Lambda env config.
EVENT_BUS_NAME = os.environ.get("BUSINESS_EVENT_BUS_NAME", "trivelta-events")


def publish_business_event(event: BusinessEvent, *, bus_name: str | None = None) -> bool:
    """Put one business event onto the custom EventBridge bus.

    Args:
        event: A BusinessEvent (UserSignedUp, KycApproved, ...).
        bus_name: Override the default bus (useful for tests / multi-bus setups).

    Returns:
        True if EventBridge accepted the event, False otherwise.
    """
    target_bus = bus_name or EVENT_BUS_NAME

    try:
        response = get_events_client().put_events(
            Entries=[
                {
                    "Source": event.source,
                    "DetailType": event.detail_type,
                    "Detail": json.dumps(event.detail(), default=str),
                    "EventBusName": target_bus,
                }
            ]
        )
    except Exception:
        logger.exception(
            "publish_business_event: put_events failed source=%s detail_type=%s",
            event.source,
            event.detail_type,
        )
        return False

    # put_events returns 200 even when individual entries fail — check the count.
    failed = response.get("FailedEntryCount", 0)
    if isinstance(failed, int) and failed > 0:
        entries = response.get("Entries") or [{}]
        err = entries[0] if isinstance(entries, list) and entries else {}
        logger.warning(
            "publish_business_event: entry rejected source=%s detail_type=%s code=%s msg=%s",
            event.source,
            event.detail_type,
            err.get("ErrorCode", "unknown") if isinstance(err, dict) else "unknown",
            err.get("ErrorMessage", "") if isinstance(err, dict) else "",
        )
        return False

    logger.info(
        "publish_business_event: published source=%s detail_type=%s bus=%s",
        event.source,
        event.detail_type,
        target_bus,
    )
    return True
