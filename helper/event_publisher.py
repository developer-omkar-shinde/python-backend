"""AWS SNS adapter for publishing domain events.

Follows the reference repo pattern:
- Accepts DomainEvent objects directly from domain_events.py
- Publishes flat event JSON as the SNS Message (no outer wrapper)
- Uses event_type as the SNS MessageAttribute for filtering
- Raises on failure by default (explicit failure > silent drop)

Reference: services/onboarding_service/onboarding/v2/infrastructure/event_publisher.py
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import ClientError

from helper.utilities import get_logger

if TYPE_CHECKING:
    from helper.domain_events import DomainEvent

logger = get_logger(__name__)


class EventPublishError(Exception):
    """Raised when a domain event fails to publish."""

    def __init__(self, event_type: str) -> None:
        super().__init__(f"Failed to publish {event_type}")


class EventPublisher:
    """Publishes domain events to AWS SNS.

    Usage:
        import boto3
        from helper.domain_events import UserCreated
        from helper.event_publisher import EventPublisher

        sns = boto3.client("sns", region_name="us-east-1")
        publisher = EventPublisher(
            sns_client=sns,
            topic_arn=os.environ["USER_EVENTS_TOPIC_ARN"],
        )

        event = UserCreated(user_id="123", email="alice@example.com", first_name="Alice", last_name="Smith")
        publisher.publish(event)
    """

    def __init__(self, sns_client: object, topic_arn: str) -> None:
        self._sns = sns_client
        self._topic_arn = topic_arn

    def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to the SNS topic.

        Publishes the flat domain event JSON as the SNS Message so consumers
        can access fields directly without unwrapping a nested envelope.

        Args:
            event: A DomainEvent instance (UserCreated, UserVerified, etc.)

        Raises:
            EventPublishError: If the SNS publish call fails.

        Example message published to SNS:
            {
                "event_type": "UserCreated",
                "event_id": "uuid-1234",
                "occurred_at": "2024-06-16T12:00:00Z",
                "user_id": "user-123",
                "email": "alice@example.com",
                "first_name": "Alice",
                "last_name": "Smith"
            }
        """
        try:
            self._sns.publish(
                TopicArn=self._topic_arn,
                Message=event.to_json(),
                MessageAttributes={
                    "event_type": {
                        "DataType": "String",
                        "StringValue": event.event_type,
                    },
                },
            )
            logger.info("Published %s", event.event_type)
        except ClientError as exc:
            logger.exception("Failed to publish %s", event.event_type)
            raise EventPublishError(event.event_type) from exc


def make_user_events_publisher(region: str = "us-east-1") -> EventPublisher:
    """Factory: create an EventPublisher wired to the user-events SNS topic.

    Topic ARN is read from the USER_EVENTS_TOPIC_ARN environment variable,
    which is set via Terraform / Lambda environment config in production.

    Args:
        region: AWS region (default: us-east-1)

    Returns:
        EventPublisher ready to publish user domain events.
    """
    sns_client = boto3.client("sns", region_name=region)
    topic_arn = os.environ.get(
        "USER_EVENTS_TOPIC_ARN",
        f"arn:aws:sns:{region}:088971275490:user-events",
    )
    return EventPublisher(sns_client=sns_client, topic_arn=topic_arn)
