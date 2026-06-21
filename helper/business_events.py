"""Typed business events published to AWS EventBridge.

An EventBridge event has three routing-relevant parts:

    {
      "source":      "onboarding.service",   <- who emitted it
      "detail-type": "user.signed_up",        <- what happened
      "detail":      { ...business payload... }
    }

EventBridge *rules* match on `source`, `detail-type`, AND fields inside
`detail` (content-based filtering). That content filtering is the key
difference from SNS, where a subscribed queue receives every message on the
topic (aside from basic attribute filter policies).

Each event below declares its own `source` and `detail_type` so the publisher
and the routing rules stay in sync with the code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4


@dataclass(frozen=True)
class BusinessEvent:
    """Base class for EventBridge business events.

    Subclasses set `source` / `detail_type` class vars and add payload fields.
    `frozen=True` keeps events immutable — they are historical facts.
    """

    source: ClassVar[str] = "onboarding.service"
    detail_type: ClassVar[str] = ""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def detail(self) -> dict:
        """Return the EventBridge `detail` payload (all fields, flat)."""
        return asdict(self)


@dataclass(frozen=True)
class UserSignedUp(BusinessEvent):
    """A new user finished sign-up."""

    detail_type: ClassVar[str] = "user.signed_up"

    user_id: str = ""
    email: str = ""
    first_name: str = ""
    country: str = ""


@dataclass(frozen=True)
class KycApproved(BusinessEvent):
    """A user's KYC verification was approved."""

    detail_type: ClassVar[str] = "kyc.approved"

    user_id: str = ""
    country: str = ""
    tier: str = ""


@dataclass(frozen=True)
class UserDeactivated(BusinessEvent):
    """A user account was deactivated."""

    detail_type: ClassVar[str] = "user.deactivated"

    user_id: str = ""
    reason: str = ""
