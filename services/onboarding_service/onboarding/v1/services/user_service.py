"""Business logic for user operations."""

from __future__ import annotations

from dataclasses import dataclass

from helper.business_event_publisher import publish_business_event
from helper.business_events import UserSignedUp
from helper.domain_events import UserCreated
from helper.event_publisher import EventPublisher
from onboarding.v1.repositories.user_repository import UserRepository
from onboarding.v1.schemas.responses.user_response import UserResponse


@dataclass
class UserServiceDeps:
    """Dependencies for UserService — avoids long __init__ signatures as the service grows."""

    user_repo: UserRepository
    event_publisher: EventPublisher


class UserService:
    def __init__(self, *, deps: UserServiceDeps) -> None:
        self._user_repo = deps.user_repo
        self._event_publisher = deps.event_publisher

    def create_user(self, first_name: str, last_name: str) -> UserResponse:
        """Create a new user and publish events.

        Flow:
        1. Save user to DynamoDB
        2. Publish UserCreated to SNS  → SQS consumers (email, preferences…)
        3. Publish UserSignedUp to EventBridge → rule-based routing
           - welcome-email-queue  (detail-type == user.signed_up)
           - analytics-queue      (source == onboarding.service catch-all)
        """
        user_data = self._user_repo.create(first_name, last_name)

        # SNS: flat domain event for simple fan-out consumers
        self._event_publisher.publish(
            UserCreated(
                user_id=user_data["user_id"],
                first_name=first_name,
                last_name=last_name,
            )
        )

        # EventBridge: business event with richer content for rule-based routing
        publish_business_event(
            UserSignedUp(
                user_id=user_data["user_id"],
                first_name=first_name,
                email="",
                country="",
            )
        )

        return UserResponse(**user_data)

    def get_user(self, user_id: str) -> UserResponse:
        """Raises UserNotFoundError if user does not exist."""
        user_data = self._user_repo.get_by_id(user_id)
        return UserResponse(**user_data)
