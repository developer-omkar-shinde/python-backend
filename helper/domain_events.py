"""Domain events for the onboarding service.

Domain events represent things that have happened in the business domain.
They are published to SNS for other services to react to.

Example flow:
1. User is created (business event happens)
2. Service publishes UserCreated event to SNS
3. Email service subscribes and sends welcome email
4. Analytics service subscribes and logs user signup
5. Feature service subscribes and initializes features for user
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class DomainEvent:
    """Base class for domain events.

    Frozen=True means events are immutable (can't be changed after creation).
    This is important because events represent historical facts that happened.
    """

    event_id: str = field(default_factory=lambda: __import__("uuid").uuid4().__str__())
    occurred_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    @property
    def event_type(self) -> str:
        """Event type is the class name."""
        return self.__class__.__name__

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        from dataclasses import asdict

        return {"event_type": self.event_type, **asdict(self)}


@dataclass(frozen=True)
class UserCreated(DomainEvent):
    """Event: A new user was created.

    This is published when a user successfully signs up.
    Subscribers might:
    - Send welcome email
    - Initialize user features
    - Log analytics
    - Create user in other systems
    """

    user_id: str = field(default="")
    first_name: str = field(default="")
    last_name: str = field(default="")
    email: str | None = field(default=None)


@dataclass(frozen=True)
class UserVerified(DomainEvent):
    """Event: User email/phone was verified."""

    user_id: str = field(default="")
    verification_type: str = field(default="")


@dataclass(frozen=True)
class UserDeleted(DomainEvent):
    """Event: User account was deleted."""

    user_id: str = field(default="")
    reason: str | None = field(default=None)


@dataclass(frozen=True)
class PaymentCompleted(DomainEvent):
    """Event: Payment was successfully processed.

    Subscribers might:
    - Update inventory
    - Send receipt email
    - Trigger fulfillment
    - Update analytics
    """

    payment_id: str = field(default="")
    user_id: str = field(default="")
    amount: float = field(default=0.0)
    currency: str = field(default="")
    payment_method: str = field(default="")


@dataclass(frozen=True)
class PaymentFailed(DomainEvent):
    """Event: Payment processing failed."""

    payment_id: str = field(default="")
    user_id: str = field(default="")
    reason: str = field(default="")


@dataclass(frozen=True)
class OrderCreated(DomainEvent):
    """Event: New order was created.

    Subscribers might:
    - Notify warehouse
    - Update inventory
    - Send confirmation email
    """

    order_id: str = field(default="")
    user_id: str = field(default="")
    total_amount: float = field(default=0.0)
    item_count: int = field(default=0)
